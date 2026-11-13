import requests
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

URL_API = "http://127.0.0.1:8000"

FOND = (0.06, 0.09, 0.16, 1)
CARTE = (0.12, 0.16, 0.25, 1)
BLEU = (0.23, 0.51, 0.96, 1)
VERT = (0.13, 0.77, 0.37, 1)
ORANGE = (0.98, 0.55, 0.12, 1)
ROUGE = (0.94, 0.27, 0.27, 1)
GRIS = (0.39, 0.45, 0.55, 1)
BLANC = (1, 1, 1, 1)
GRIS_CLAIR = (0.62, 0.68, 0.78, 1)

Window.clearcolor = FOND


class Carte(BoxLayout):

    def __init__(self, couleur=CARTE, rayon=14, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*couleur)
            self.fond = RoundedRectangle(pos=self.pos, size=self.size, radius=[rayon])
        self.bind(pos=self.maj_fond, size=self.maj_fond)

    def maj_fond(self, *args):
        self.fond.pos = self.pos
        self.fond.size = self.size


class BoutonRond(Button):

    def __init__(self, couleur=BLEU, **kwargs):
        super().__init__(
            background_normal="",
            background_color=(0, 0, 0, 0),
            bold=True,
            **kwargs
        )
        with self.canvas.before:
            Color(*couleur)
            self.fond = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self.bind(pos=self.maj_fond, size=self.maj_fond)

    def maj_fond(self, *args):
        self.fond.pos = self.pos
        self.fond.size = self.size


def texte_gauche(texte, **kwargs):
    label = Label(text=texte, halign="left", valign="middle", **kwargs)
    label.bind(size=label.setter("text_size"))
    return label


def creer_stat(titre, couleur):
    carte = Carte(orientation="vertical", padding=10)
    chiffre = Label(text="0", font_size=26, bold=True, color=couleur)
    carte.add_widget(chiffre)
    carte.add_widget(Label(text=titre, font_size=12, color=GRIS_CLAIR))
    return carte, chiffre


def ajouter_champ(contenu, titre, champ):
    contenu.add_widget(texte_gauche(titre, size_hint_y=None, height=20,
                                    font_size=12, color=GRIS_CLAIR))
    champ.size_hint_y = None
    champ.height = 38
    contenu.add_widget(champ)


class EcranProduits(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=14, spacing=10, **kwargs)
        self.produits = []

        entete = BoxLayout(orientation="vertical", size_hint_y=None, height=60)
        entete.add_widget(texte_gauche("StockFlow", font_size=28, bold=True, color=BLANC))
        entete.add_widget(texte_gauche("Gestion des stocks et approvisionnements",
                                       font_size=12, color=GRIS_CLAIR))
        self.add_widget(entete)

        stats = BoxLayout(size_hint_y=None, height=80, spacing=10)
        carte1, self.stat_total = creer_stat("Produits", BLEU)
        carte2, self.stat_faible = creer_stat("Stock faible", ROUGE)
        carte3, self.stat_valeur = creer_stat("Valeur du stock", VERT)
        stats.add_widget(carte1)
        stats.add_widget(carte2)
        stats.add_widget(carte3)
        self.add_widget(stats)

        self.recherche = TextInput(hint_text="Rechercher un produit...", multiline=False,
                                   size_hint_y=None, height=42)
        self.recherche.bind(text=self.sur_recherche)
        self.add_widget(self.recherche)

        defilement = ScrollView()
        self.liste = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.liste.bind(minimum_height=self.liste.setter("height"))
        defilement.add_widget(self.liste)
        self.add_widget(defilement)

        boutons = BoxLayout(size_hint_y=None, height=48, spacing=8)

        btn_ajout = BoutonRond(text="Ajouter un produit", couleur=BLEU)
        btn_ajout.bind(on_press=self.ouvrir_ajout)
        boutons.add_widget(btn_ajout)

        btn_mouvement = BoutonRond(text="Mouvement de stock", couleur=VERT)
        btn_mouvement.bind(on_press=self.ouvrir_mouvement)
        boutons.add_widget(btn_mouvement)

        btn_historique = BoutonRond(text="Historique", couleur=ORANGE)
        btn_historique.bind(on_press=self.ouvrir_historique)
        boutons.add_widget(btn_historique)

        btn_actualiser = BoutonRond(text="Actualiser", couleur=GRIS)
        btn_actualiser.bind(on_press=self.charger_produits)
        boutons.add_widget(btn_actualiser)

        self.add_widget(boutons)

        self.charger_produits()

    def charger_produits(self, *args):
        try:
            reponse = requests.get(URL_API + "/products/", timeout=5)
            self.produits = reponse.json()
        except requests.exceptions.RequestException:
            self.produits = []
            self.liste.clear_widgets()
            self.liste.add_widget(Label(text="Impossible de joindre l'API",
                                        size_hint_y=None, height=40, color=ROUGE))
            return
        self.afficher_produits()

    def sur_recherche(self, instance, valeur):
        self.afficher_produits()

    def afficher_produits(self):
        total = len(self.produits)
        nb_faibles = 0
        valeur_stock = 0
        for p in self.produits:
            if p["quantity"] <= p["min_quantity"]:
                nb_faibles += 1
            valeur_stock += p["quantity"] * p["purchase_price"]

        self.stat_total.text = str(total)
        self.stat_faible.text = str(nb_faibles)
        self.stat_valeur.text = f"{valeur_stock:,.0f}".replace(",", " ")

        mot = self.recherche.text.strip().lower()
        self.liste.clear_widgets()
        for p in self.produits:
            if mot != "" and mot not in p["name"].lower() and mot not in p["reference"].lower():
                continue
            self.liste.add_widget(self.creer_ligne(p))

    def creer_ligne(self, p):
        en_faible = p["quantity"] <= p["min_quantity"]
        couleur = ROUGE if en_faible else VERT

        ligne = Carte(orientation="horizontal", size_hint_y=None, height=70,
                      padding=12, spacing=10)
        ligne.bind(on_touch_down=lambda inst, touch, prod=p: self.sur_clic_ligne(inst, touch, prod))

        infos = BoxLayout(orientation="vertical")
        infos.add_widget(texte_gauche(p["name"], bold=True, font_size=16, color=BLANC))
        prix = f"{p['selling_price']:,.0f}".replace(",", " ")
        infos.add_widget(texte_gauche(f"Réf. {p['reference']}  -  Prix de vente : {prix}",
                                      font_size=12, color=GRIS_CLAIR))
        ligne.add_widget(infos)

        ligne.add_widget(Label(text=str(p["quantity"]), bold=True, font_size=24,
                               color=couleur, size_hint_x=None, width=60))

        badge = Carte(couleur=couleur, rayon=10, size_hint=(None, None),
                      size=(110, 28), pos_hint={"center_y": 0.5})
        texte_badge = "STOCK FAIBLE" if en_faible else "EN STOCK"
        badge.add_widget(Label(text=texte_badge, bold=True, font_size=11, color=BLANC))
        ligne.add_widget(badge)

        return ligne

    def sur_clic_ligne(self, ligne, touch, produit):
        if not ligne.collide_point(*touch.pos):
            return
        if getattr(touch, "is_mouse_scrolling", False):
            return
        if getattr(touch, "button", "left") != "left":
            return
        self.ouvrir_modification(produit)

    # ==================== Ajouter un produit ====================
    def ouvrir_ajout(self, *args):
        contenu = BoxLayout(orientation="vertical", padding=10, spacing=6)

        self.ajout_nom = TextInput(multiline=False)
        self.ajout_ref = TextInput(multiline=False)
        self.ajout_prix_achat = TextInput(multiline=False, input_filter="float")
        self.ajout_prix_vente = TextInput(multiline=False, input_filter="float")
        self.ajout_quantite = TextInput(multiline=False, input_filter="int")
        self.ajout_minimum = TextInput(text="5", multiline=False, input_filter="int")
        self.ajout_message = Label(text="", color=ROUGE)

        ajouter_champ(contenu, "Nom du produit", self.ajout_nom)
        ajouter_champ(contenu, "Référence (ex : EAU002)", self.ajout_ref)
        ajouter_champ(contenu, "Prix d'achat", self.ajout_prix_achat)
        ajouter_champ(contenu, "Prix de vente", self.ajout_prix_vente)
        ajouter_champ(contenu, "Quantité initiale", self.ajout_quantite)
        ajouter_champ(contenu, "Stock minimum", self.ajout_minimum)
        contenu.add_widget(self.ajout_message)

        boutons = BoxLayout(size_hint_y=None, height=48, spacing=10)
        btn_ok = BoutonRond(text="Enregistrer", couleur=BLEU)
        btn_annuler = BoutonRond(text="Annuler", couleur=GRIS)
        boutons.add_widget(btn_ok)
        boutons.add_widget(btn_annuler)
        contenu.add_widget(boutons)

        self.fenetre_ajout = Popup(title="Nouveau produit", content=contenu,
                                   size_hint=(0.85, 0.95))
        btn_ok.bind(on_press=self.enregistrer_produit)
        btn_annuler.bind(on_press=self.fenetre_ajout.dismiss)
        self.fenetre_ajout.open()

    def enregistrer_produit(self, *args):
        nom = self.ajout_nom.text.strip()
        ref = self.ajout_ref.text.strip()
        if nom == "" or ref == "":
            self.ajout_message.text = "Le nom et la référence sont obligatoires"
            return

        donnees = {
            "name": nom,
            "reference": ref,
            "purchase_price": float(self.ajout_prix_achat.text or 0),
            "selling_price": float(self.ajout_prix_vente.text or 0),
            "quantity": int(self.ajout_quantite.text or 0),
            "min_quantity": int(self.ajout_minimum.text or 5),
        }
        try:
            reponse = requests.post(URL_API + "/products/", json=donnees, timeout=5)
        except requests.exceptions.RequestException:
            self.ajout_message.text = "Impossible de joindre l'API"
            return

        if reponse.status_code == 200:
            self.fenetre_ajout.dismiss()
            self.charger_produits()
        else:
            self.ajout_message.text = reponse.json().get("detail", "Erreur")

    def ouvrir_modification(self, produit):
        contenu = BoxLayout(orientation="vertical", padding=10, spacing=6)

        self.modif_nom = TextInput(text=produit["name"], multiline=False)
        self.modif_prix_achat = TextInput(text=str(produit["purchase_price"]),
                                          multiline=False, input_filter="float")
        self.modif_prix_vente = TextInput(text=str(produit["selling_price"]),
                                          multiline=False, input_filter="float")
        self.modif_minimum = TextInput(text=str(produit["min_quantity"]),
                                       multiline=False, input_filter="int")
        self.modif_message = Label(text="", color=ROUGE)

        contenu.add_widget(Label(text="Référence : " + produit["reference"],
                                 size_hint_y=None, height=25, color=GRIS_CLAIR))
        ajouter_champ(contenu, "Nom", self.modif_nom)
        ajouter_champ(contenu, "Prix d'achat", self.modif_prix_achat)
        ajouter_champ(contenu, "Prix de vente", self.modif_prix_vente)
        ajouter_champ(contenu, "Stock minimum", self.modif_minimum)
        contenu.add_widget(self.modif_message)

        boutons = BoxLayout(size_hint_y=None, height=48, spacing=10)
        btn_ok = BoutonRond(text="Enregistrer", couleur=BLEU)
        btn_suppr = BoutonRond(text="Supprimer", couleur=ROUGE)
        btn_annuler = BoutonRond(text="Annuler", couleur=GRIS)
        boutons.add_widget(btn_ok)
        boutons.add_widget(btn_suppr)
        boutons.add_widget(btn_annuler)
        contenu.add_widget(boutons)

        self.fenetre_modif = Popup(title="Modifier le produit", content=contenu,
                                   size_hint=(0.85, 0.9))
        btn_ok.bind(on_press=lambda x: self.modifier_produit(produit["id"]))
        btn_suppr.bind(on_press=lambda x: self.supprimer_produit(produit["id"]))
        btn_annuler.bind(on_press=self.fenetre_modif.dismiss)
        self.fenetre_modif.open()

    def modifier_produit(self, id_produit):
        nom = self.modif_nom.text.strip()
        if nom == "":
            self.modif_message.text = "Le nom est obligatoire"
            return

        donnees = {
            "name": nom,
            "purchase_price": float(self.modif_prix_achat.text or 0),
            "selling_price": float(self.modif_prix_vente.text or 0),
            "min_quantity": int(self.modif_minimum.text or 5),
        }
        try:
            reponse = requests.put(URL_API + "/products/" + str(id_produit),
                                   json=donnees, timeout=5)
        except requests.exceptions.RequestException:
            self.modif_message.text = "Impossible de joindre l'API"
            return

        if reponse.status_code == 200:
            self.fenetre_modif.dismiss()
            self.charger_produits()
        else:
            self.modif_message.text = reponse.json().get("detail", "Erreur")

    def supprimer_produit(self, id_produit):
        try:
            reponse = requests.delete(URL_API + "/products/" + str(id_produit), timeout=5)
        except requests.exceptions.RequestException:
            self.modif_message.text = "Impossible de joindre l'API"
            return

        if reponse.status_code == 200:
            self.fenetre_modif.dismiss()
            self.charger_produits()
        else:
            self.modif_message.text = reponse.json().get("detail", "Erreur")

    def ouvrir_mouvement(self, *args):
        contenu = BoxLayout(orientation="vertical", padding=10, spacing=6)

        self.mvt_ref = TextInput(multiline=False)
        self.mvt_quantite = TextInput(multiline=False, input_filter="int")
        self.mvt_description = TextInput(multiline=False)
        self.mvt_message = Label(text="", color=ROUGE)

        ajouter_champ(contenu, "Référence du produit (ex : EAU001)", self.mvt_ref)
        ajouter_champ(contenu, "Quantité", self.mvt_quantite)
        ajouter_champ(contenu, "Description (facultatif)", self.mvt_description)
        contenu.add_widget(self.mvt_message)

        boutons = BoxLayout(size_hint_y=None, height=48, spacing=10)
        btn_entree = BoutonRond(text="Entrée (+)", couleur=VERT)
        btn_sortie = BoutonRond(text="Sortie (-)", couleur=ROUGE)
        btn_annuler = BoutonRond(text="Annuler", couleur=GRIS)
        boutons.add_widget(btn_entree)
        boutons.add_widget(btn_sortie)
        boutons.add_widget(btn_annuler)
        contenu.add_widget(boutons)

        self.fenetre_mvt = Popup(title="Mouvement de stock", content=contenu,
                                 size_hint=(0.85, 0.75))
        btn_entree.bind(on_press=lambda x: self.enregistrer_mouvement("entree"))
        btn_sortie.bind(on_press=lambda x: self.enregistrer_mouvement("sortie"))
        btn_annuler.bind(on_press=self.fenetre_mvt.dismiss)
        self.fenetre_mvt.open()

    def enregistrer_mouvement(self, type_mvt):
        ref = self.mvt_ref.text.strip()
        if ref == "" or self.mvt_quantite.text == "":
            self.mvt_message.text = "La référence et la quantité sont obligatoires"
            return

        produit_trouve = None
        for p in self.produits:
            if p["reference"] == ref:
                produit_trouve = p
        if produit_trouve is None:
            self.mvt_message.text = "Référence introuvable"
            return

        donnees = {
            "product_id": produit_trouve["id"],
            "movement_type": type_mvt,
            "quantity": int(self.mvt_quantite.text),
            "description": self.mvt_description.text.strip() or None,
        }
        try:
            reponse = requests.post(URL_API + "/movements/", json=donnees, timeout=5)
        except requests.exceptions.RequestException:
            self.mvt_message.text = "Impossible de joindre l'API"
            return

        if reponse.status_code == 200:
            self.fenetre_mvt.dismiss()
            self.charger_produits()
        else:
            self.mvt_message.text = reponse.json().get("detail", "Erreur")

    def ouvrir_historique(self, *args):
        contenu = BoxLayout(orientation="vertical", padding=10, spacing=10)

        defilement = ScrollView()
        liste = GridLayout(cols=1, spacing=6, size_hint_y=None)
        liste.bind(minimum_height=liste.setter("height"))
        defilement.add_widget(liste)
        contenu.add_widget(defilement)

        btn_fermer = BoutonRond(text="Fermer", couleur=GRIS, size_hint_y=None, height=48)
        contenu.add_widget(btn_fermer)

        try:
            mouvements = requests.get(URL_API + "/movements/", timeout=5).json()
        except requests.exceptions.RequestException:
            mouvements = []
            liste.add_widget(Label(text="Impossible de joindre l'API",
                                   size_hint_y=None, height=40, color=ROUGE))

        noms = {}
        for p in self.produits:
            noms[p["id"]] = p["name"]

        for m in mouvements:
            if m["movement_type"] == "entree":
                couleur = VERT
                signe = "+"
            else:
                couleur = ROUGE
                signe = "-"
            date = m["date"][:16].replace("T", " ")

            ligne = Carte(orientation="horizontal", size_hint_y=None, height=50,
                          padding=10, spacing=10)
            ligne.add_widget(Label(text=signe + str(m["quantity"]), bold=True, font_size=18,
                                   color=couleur, size_hint_x=None, width=60))

            infos = BoxLayout(orientation="vertical")
            infos.add_widget(texte_gauche(noms.get(m["product_id"], "?"), bold=True,
                                          font_size=14, color=BLANC))
            detail = date
            if m.get("description"):
                detail = detail + "  -  " + m["description"]
            infos.add_widget(texte_gauche(detail, font_size=11, color=GRIS_CLAIR))
            ligne.add_widget(infos)

            liste.add_widget(ligne)

        fenetre = Popup(title="Historique des mouvements", content=contenu,
                        size_hint=(0.92, 0.85))
        btn_fermer.bind(on_press=fenetre.dismiss)
        fenetre.open()


class StockFlowApp(App):
    title = "StockFlow"

    def build(self):
        return EcranProduits()


if __name__ == "__main__":
    StockFlowApp().run()