import json
import os
import sqlite3
from datetime import datetime

import tornado.ioloop
import tornado.web

# La base de données est créée à côté de ce fichier
CHEMIN_BD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stockflow.db")


# ==================== Base de données ====================
def connexion():
    """Ouvre une connexion à la base de données."""
    bd = sqlite3.connect(CHEMIN_BD)
    bd.row_factory = sqlite3.Row
    return bd


def creer_tables():
    """Crée les tables si elles n'existent pas encore."""
    bd = connexion()
    bd.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            reference TEXT NOT NULL UNIQUE,
            purchase_price REAL DEFAULT 0,
            selling_price REAL DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            min_quantity INTEGER DEFAULT 5
        )
    """)
    bd.execute("""
        CREATE TABLE IF NOT EXISTS movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            description TEXT,
            date TEXT NOT NULL
        )
    """)
    bd.commit()
    bd.close()


# ==================== Outils ====================
class BaseHandler(tornado.web.RequestHandler):
    """Fonctions communes à toutes les routes."""

    def envoyer_json(self, donnees, code=200):
        self.set_status(code)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.write(json.dumps(donnees))

    def erreur(self, message, code=400):
        # L'interface lit la clé "detail" quand il y a une erreur
        self.envoyer_json({"detail": message}, code)

    def lire_donnees(self):
        """Lit le JSON envoyé par l'interface. Renvoie None si invalide."""
        try:
            return json.loads(self.request.body)
        except ValueError:
            return None


def trouver_produit(bd, id_produit):
    ligne = bd.execute("SELECT * FROM products WHERE id = ?", (id_produit,)).fetchone()
    if ligne is None:
        return None
    return dict(ligne)


# ==================== Produits ====================
class ProduitsHandler(BaseHandler):
    def get(self):
        bd = connexion()
        lignes = bd.execute("SELECT * FROM products ORDER BY name").fetchall()
        bd.close()
        self.envoyer_json([dict(l) for l in lignes])

    def post(self):
        donnees = self.lire_donnees()
        if donnees is None:
            return self.erreur("Données invalides")

        nom = str(donnees.get("name", "")).strip()
        ref = str(donnees.get("reference", "")).strip()
        if nom == "" or ref == "":
            return self.erreur("Le nom et la référence sont obligatoires")

        bd = connexion()
        existe = bd.execute("SELECT id FROM products WHERE reference = ?", (ref,)).fetchone()
        if existe is not None:
            bd.close()
            return self.erreur("Cette référence existe déjà")

        curseur = bd.execute(
            "INSERT INTO products (name, reference, purchase_price, selling_price, quantity, min_quantity) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nom, ref,
             float(donnees.get("purchase_price", 0)),
             float(donnees.get("selling_price", 0)),
             int(donnees.get("quantity", 0)),
             int(donnees.get("min_quantity", 5))),
        )
        bd.commit()
        produit = trouver_produit(bd, curseur.lastrowid)
        bd.close()
        self.envoyer_json(produit)


class ProduitHandler(BaseHandler):
    def put(self, id_produit):
        donnees = self.lire_donnees()
        if donnees is None:
            return self.erreur("Données invalides")

        bd = connexion()
        produit = trouver_produit(bd, int(id_produit))
        if produit is None:
            bd.close()
            return self.erreur("Produit introuvable", 404)

        nom = str(donnees.get("name", produit["name"])).strip()
        if nom == "":
            bd.close()
            return self.erreur("Le nom est obligatoire")

        bd.execute(
            "UPDATE products SET name = ?, purchase_price = ?, selling_price = ?, min_quantity = ? WHERE id = ?",
            (nom,
             float(donnees.get("purchase_price", produit["purchase_price"])),
             float(donnees.get("selling_price", produit["selling_price"])),
             int(donnees.get("min_quantity", produit["min_quantity"])),
             int(id_produit)),
        )
        bd.commit()
        produit = trouver_produit(bd, int(id_produit))
        bd.close()
        self.envoyer_json(produit)

    def delete(self, id_produit):
        bd = connexion()
        produit = trouver_produit(bd, int(id_produit))
        if produit is None:
            bd.close()
            return self.erreur("Produit introuvable", 404)

        # On supprime aussi l'historique de ce produit
        bd.execute("DELETE FROM movements WHERE product_id = ?", (int(id_produit),))
        bd.execute("DELETE FROM products WHERE id = ?", (int(id_produit),))
        bd.commit()
        bd.close()
        self.envoyer_json({"detail": "Produit supprimé"})


# ==================== Mouvements ====================
class MouvementsHandler(BaseHandler):
    def get(self):
        bd = connexion()
        lignes = bd.execute("SELECT * FROM movements ORDER BY date DESC, id DESC").fetchall()
        bd.close()
        self.envoyer_json([dict(l) for l in lignes])

    def post(self):
        donnees = self.lire_donnees()
        if donnees is None:
            return self.erreur("Données invalides")

        type_mvt = donnees.get("movement_type")
        if type_mvt not in ("entree", "sortie"):
            return self.erreur("Type de mouvement invalide")

        try:
            quantite = int(donnees.get("quantity"))
            id_produit = int(donnees.get("product_id"))
        except (TypeError, ValueError):
            return self.erreur("Quantité ou produit invalide")

        if quantite <= 0:
            return self.erreur("La quantité doit être supérieure à 0")

        bd = connexion()
        produit = trouver_produit(bd, id_produit)
        if produit is None:
            bd.close()
            return self.erreur("Produit introuvable", 404)

        # On calcule la nouvelle quantité en stock
        if type_mvt == "entree":
            nouvelle_quantite = produit["quantity"] + quantite
        else:
            if quantite > produit["quantity"]:
                bd.close()
                return self.erreur("Stock insuffisant")
            nouvelle_quantite = produit["quantity"] - quantite

        date = datetime.now().isoformat(timespec="seconds")
        curseur = bd.execute(
            "INSERT INTO movements (product_id, movement_type, quantity, description, date) "
            "VALUES (?, ?, ?, ?, ?)",
            (id_produit, type_mvt, quantite, donnees.get("description"), date),
        )
        bd.execute("UPDATE products SET quantity = ? WHERE id = ?", (nouvelle_quantite, id_produit))
        bd.commit()
        mouvement = dict(bd.execute("SELECT * FROM movements WHERE id = ?", (curseur.lastrowid,)).fetchone())
        bd.close()
        self.envoyer_json(mouvement)


# ==================== Lancement ====================
def creer_application():
    # Le dossier dashboard est à côté du dossier backend
    dossier_backend = os.path.dirname(os.path.abspath(__file__))
    dossier_dashboard = os.path.join(os.path.dirname(dossier_backend), "dashboard")

    return tornado.web.Application([
        (r"/products/?", ProduitsHandler),
        (r"/products/(\d+)/?", ProduitHandler),
        (r"/movements/?", MouvementsHandler),
        (r"/dashboard/(.*)", tornado.web.StaticFileHandler,
         {"path": dossier_dashboard, "default_filename": "index.html"}),
    ])


if __name__ == "__main__":
    creer_tables()
    app = creer_application()
    app.listen(8000, address="127.0.0.1")
    print("Serveur StockFlow lancé sur http://127.0.0.1:8000 (Ctrl + C pour arrêter)")
    tornado.ioloop.IOLoop.current().start()