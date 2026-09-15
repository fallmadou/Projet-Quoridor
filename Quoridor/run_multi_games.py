# Importe le module sys pour pouvoir modifier le chemin de recherche
# des modules Python.
import sys

# Permet notamment de manipuler les fichiers et les chemins.
import os

# Permet de créer et d'écrire des fichiers CSV.
import csv

# Permet de mesurer le temps d'exécution d'une partie.
import time


# Importe différentes fonctions utiles pour manipuler les chemins de fichiers :
# - basename() : récupère le nom du fichier
# - splitext() : sépare le nom du fichier de son extension
# - dirname() : récupère le dossier contenant le fichier
from os.path import basename, splitext, dirname


# Classes nécessaires au fonctionnement du jeu Quoridor.
from board_quoridor import BoardQuoridor
from game_state_quoridor import GameStateQuoridor
from master_quoridor import MasterQuoridor

# Permet d'exécuter les joueurs dans des conteneurs/proxys
# compatibles avec le moteur Seahorse.
from seahorse.player.proxies import ContaineredPlayerProxy


# Nom du fichier contenant notre joueur.
MY_PLAYER = "my_player_V1.py"

# Nom du fichier contenant le joueur adverse.
OPPS_PLAYER = "random_player_quoridor.py"

# Nombre total de parties à jouer.
N_GAMES = 2


def play_one_game(game_number):
    """
    Lance une partie entre MyPlayer et OPPSPlayer.

    Retourne :
        - le nom du gagnant
        - le nombre de coups joués
        - le temps nécessaire pour terminer la partie
    """

    # Récupère le dossier dans lequel se trouve MyPlayer.
    folder = dirname(MY_PLAYER)

    # Ajoute ce dossier aux chemins dans lesquels Python
    # recherche les modules.
    sys.path.append(folder)

    # Importe dynamiquement le fichier my_player_V1.py.
    my_module = __import__(
        splitext(basename(MY_PLAYER))[0],
        fromlist=[None]
    )


    # Même principe pour l'autre joueur.
    folder = dirname(OPPS_PLAYER)
    sys.path.append(folder)

    # Importe dynamiquement le fichier adverse.
    opps_module = __import__(
        splitext(basename(OPPS_PLAYER))[0],
        fromlist=[None]
    )


    # Création du premier joueur.
    #
    # "W" correspond à sa couleur.
    # goal_row=0 signifie que son objectif est d'atteindre
    # la ligne 0 du plateau.
    player1 = ContaineredPlayerProxy(
        my_module.MyPlayer(
            "W",
            goal_row=0,
            name="MyPlayer"
        ),
        gs=GameStateQuoridor
    )


    # Création du deuxième joueur.
    #
    # "B" correspond à sa couleur.
    # Son objectif est d'atteindre la ligne 8.
    player2 = ContaineredPlayerProxy(
        opps_module.MyPlayer(
            "B",
            goal_row=8,
            name="OPPSPlayer"
        ),
        gs=GameStateQuoridor
    )


    # Stocke les deux joueurs dans une liste.
    players = [player1, player2]


    # Création de la représentation initiale du plateau.
    init_rep = BoardQuoridor(
        {
            # MyPlayer commence en bas du plateau,
            # sur la ligne 8, colonne 4.
            player1.get_id(): (8, 4),

            # OPPSPlayer commence en haut,
            # sur la ligne 0, colonne 4.
            player2.get_id(): (0, 4)
        },

        # Aucun mur n'est placé au début de la partie.
        frozenset(),

        # Chaque joueur commence avec 10 murs.
        {
            player1.get_id(): 10,
            player2.get_id(): 10
        }
    )


    # Création de l'état initial de la partie.
    initial_state = GameStateQuoridor(
        {
            # Chaque joueur commence avec 0 point.
            player1.get_id(): 0,
            player2.get_id(): 0
        },

        # Le premier joueur à jouer est player1.
        player1.to_player(),

        # Liste des joueurs participant à la partie.
        players=[
            player1.to_player(),
            player2.to_player()
        ],

        # Représentation initiale du plateau.
        rep=init_rep,

        # La partie commence au coup 0.
        step=0
    )


    # Création du moteur qui va gérer la partie.
    master = MasterQuoridor(
        # Nom du jeu.
        name="Quoridor",

        # État initial de la partie.
        initial_game_state=initial_state,

        # Ordre dans lequel les joueurs jouent.
        players_iterator=players,

        # Niveau de logs.
        log_level="ERROR",

        # Chaque partie utilise un port différent.
        port=16001 + game_number,

        # Le serveur fonctionne sur la machine locale.
        hostname="localhost",

        # Temps maximum autorisé pour une partie :
        # 15 minutes.
        time_limit=15 * 60
    )


    # Enregistre le moment où la partie commence.
    start = time.time()

    # Lance réellement la partie.
    master.record_game(listeners=[])

    # Calcule la durée totale de la partie.
    elapsed = time.time() - start


    # Récupère la liste des gagnants.
    winners = master.compute_winner()

    # Récupère le nom du premier gagnant.
    winner = winners[0].get_name()


    # Récupère le nombre de coups joués pendant la partie.
    moves = master.current_game_state.get_step()


    # Renvoie les informations importantes de la partie.
    return winner, moves, elapsed


def main():
    """
    Lance les N_GAMES parties et affiche les résultats.
    Les résultats sont sauvegardés dans deux fichiers CSV :
        - détails de chaque partie
        - statistiques globales
    """

    # Liste contenant les résultats de chaque partie.
    results = []

    # Compteurs de victoires.
    my_wins = 0
    opps_wins = 0

    # Compteur de parties terminées avec succès.
    games_played = 0

    # Temps total de toutes les parties.
    total_time = 0

    # Nombre total de coups joués.
    total_moves = 0


    # Affichage du titre du programme.
    print("=" * 50)
    print("MyPlayer vs OPPSPlayer")
    print(f"{N_GAMES} parties")
    print("=" * 50)


    # Lance les parties une par une.
    for i in range(1, N_GAMES + 1):

        # Affiche la progression.
        print(f"Partie {i}/{N_GAMES}...", end=" ")


        # try permet d'éviter que le programme entier
        # s'arrête si une partie rencontre une erreur.
        try:

            # Lance une partie et récupère ses résultats.
            winner, moves, elapsed = play_one_game(i)

            # Incrémente le nombre de parties terminées.
            games_played += 1

            # Compte les victoires de chaque joueur.
            if "MyPlayer" in winner:
                my_wins += 1
            else:
                opps_wins += 1

            # Ajoute le temps et le nombre de coups
            # aux totaux pour calculer les moyennes.
            total_time += elapsed
            total_moves += moves


            # Ajoute les informations de la partie
            # dans la liste des résultats.
            results.append([
                i,                  # Numéro de la partie
                winner,             # Nom du gagnant
                moves,              # Nombre de coups
                round(elapsed, 3)   # Temps en secondes
            ])


            # Affiche le résultat de la partie.
            print(
                f"Gagnant: {winner} | "
                f"coups: {moves} | "
                f"temps: {elapsed:.2f}s"
            )


        # Si une erreur survient pendant une partie,
        # elle est affichée mais le programme continue
        # avec la partie suivante.
        except Exception as e:
            print(f"ERREUR: {e}")


    # ---------------------------------------------------------
    # CALCUL DES STATISTIQUES GLOBALES
    # ---------------------------------------------------------

    # Évite une division par zéro si aucune partie n'a réussi.
    if games_played > 0:

        # Taux de victoire de MyPlayer.
        win_rate = my_wins / games_played * 100

        # Nombre moyen de coups par partie.
        avg_moves = total_moves / games_played

        # Temps moyen d'une partie.
        avg_time = total_time / games_played

    else:
        win_rate = 0
        avg_moves = 0
        avg_time = 0


    # Trouve le nombre maximum de coups parmi les parties réussies.
    max_moves = max(
        [result[2] for result in results],
        default=0
    )

    # Trouve le nombre minimum de coups parmi les parties réussies.
    min_moves = min(
        [result[2] for result in results],
        default=0
    )


    # ---------------------------------------------------------
    # AFFICHAGE DES RÉSULTATS
    # ---------------------------------------------------------

    print()
    print("=" * 50)
    print("RÉSULTATS")
    print("=" * 50)

    print(f"Parties demandées : {N_GAMES}")
    print(f"Parties terminées  : {games_played}")
    print(f"MyPlayer           : {my_wins}")
    print(f"OPPSPlayer         : {opps_wins}")
    print(f"Taux victoire      : {win_rate:.1f}%")
    print(f"Coups moyens       : {avg_moves:.2f}")
    print(f"Temps moyen        : {avg_time:.3f}s")
    print(f"Temps total        : {total_time:.3f}s")
    print(f"Maximum de coups   : {max_moves}")
    print(f"Minimum de coups   : {min_moves}")


    # ---------------------------------------------------------
    # SAUVEGARDE DES RÉSULTATS DÉTAILLÉS
    # ---------------------------------------------------------

    # Nom du fichier CSV détaillé.
    results_filename = f"resultats_{N_GAMES}_parties.csv"

    # Ouvre/crée le fichier CSV en mode écriture.
    with open(
        results_filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        # Création de l'objet permettant d'écrire dans le CSV.
        writer = csv.writer(file)

        # Écrit la première ligne du fichier.
        writer.writerow([
            "partie",
            "gagnant",
            "nombre_coups",
            "temps_secondes"
        ])

        # Écrit toutes les lignes correspondant aux parties.
        writer.writerows(results)


    # ---------------------------------------------------------
    # SAUVEGARDE DES STATISTIQUES GLOBALES
    # ---------------------------------------------------------

    # Nom du fichier CSV des statistiques.
    stats_filename = f"statistiques_{N_GAMES}_parties.csv"

    # Ouvre/crée le fichier de statistiques.
    with open(
        stats_filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        # Création de l'objet permettant d'écrire dans le CSV.
        writer = csv.writer(file)

        # Écrit les noms des colonnes.
        writer.writerow([
            "statistique",
            "valeur"
        ])

        # Nombre total de parties demandées.
        writer.writerow([
            "Nombre de parties demandées",
            N_GAMES
        ])

        # Nombre de parties terminées avec succès.
        writer.writerow([
            "Parties terminées",
            games_played
        ])

        # Nombre de victoires de MyPlayer.
        writer.writerow([
            "Victoires MyPlayer",
            my_wins
        ])

        # Nombre de victoires de OPPSPlayer.
        writer.writerow([
            "Victoires OPPSPlayer",
            opps_wins
        ])

        # Taux de victoire de MyPlayer.
        writer.writerow([
            "Taux de victoire MyPlayer (%)",
            round(win_rate, 2)
        ])

        # Nombre moyen de coups par partie.
        writer.writerow([
            "Nombre moyen de coups",
            round(avg_moves, 2)
        ])

        # Temps moyen d'une partie.
        writer.writerow([
            "Temps moyen par partie (secondes)",
            round(avg_time, 3)
        ])

        # Temps total de toutes les parties.
        writer.writerow([
            "Temps total (secondes)",
            round(total_time, 3)
        ])

        # Partie avec le plus de coups.
        writer.writerow([
            "Nombre maximum de coups",
            max_moves
        ])

        # Partie avec le moins de coups.
        writer.writerow([
            "Nombre minimum de coups",
            min_moves
        ])


    # ---------------------------------------------------------
    # CONFIRMATION DE LA SAUVEGARDE
    # ---------------------------------------------------------

    print()
    print("Résultats sauvegardés dans :")
    print(results_filename)
    print(stats_filename)


# Cette condition vérifie que le fichier est exécuté directement.
if __name__ == "__main__":
    main()