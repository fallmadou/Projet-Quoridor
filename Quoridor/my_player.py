from player_quoridor import PlayerQuoridor
from seahorse.game.action import Action
from game_state_quoridor import GameStateQuoridor
from seahorse.utils.custom_exceptions import MethodNotImplementedError


# class MyPlayer(PlayerQuoridor):
#     """
#     Player class for Quoridor game

#     Attributes:
#         piece_type (str): piece type of the player
#     """

#     def __init__(self, piece_type: str, goal_row: int=0, name: str = "bob", *args, **kwargs) -> None:
#         """
#         Initialize the PlayerQuoridor instance.

#         Args:
#             piece_type (str): Type of the player's game piece
#             goal_row (int): The row the player wants to reach
#             name (str, optional): Name of the player (default is "bob")
#         """
#         super().__init__(piece_type, goal_row, name)

#     def compute_action(self, current_state: GameStateQuoridor, remaining_time: float = 15*60, **kwargs) -> Action:
#         """
#         Use the minimax algorithm to choose the best action based on the heuristic evaluation of game states.

#         Args:
#             current_state (GameStateQuoridor): The current game state.

#         Returns:
#             Action: The best action as determined by minimax.
#         """

#         #TODO
#         raise MethodNotImplementedError()


# Nom(s) et matricule(s) : A COMPLETER
# INF8175 - Automne 2026 - Projet Quoridor - Version V1

import time

from player_quoridor import PlayerQuoridor
from seahorse.game.action import Action
from game_state_quoridor import GameStateQuoridor
from seahorse.utils.custom_exceptions import MethodNotImplementedError


class MyPlayer(PlayerQuoridor):
    """
    Player class for Quoridor game.

    ===========================================================================
    VERSION V1 - minimax + elagage alpha-beta, profondeur fixe, heuristique
    de "course" basee sur la distance la plus courte vers la ligne d'arrivee.
    ===========================================================================

    METHODE CHOISIE ET POURQUOI (a reprendre/adapter dans le rapport)
    -------------------------------------------------------------------------
    1) Algorithme de recherche : MINIMAX avec ELAGAGE ALPHA-BETA.
       - Quoridor est un jeu a 2 joueurs, a somme nulle (un seul gagnant),
         a information parfaite (les deux joueurs voient tout le plateau) :
         c'est exactement le cadre pour lequel minimax a ete concu.
       - L'alpha-beta ne change PAS le resultat de minimax (le coup choisi
         est identique), il coupe seulement les branches de l'arbre qui ne
         peuvent plus influencer la decision -> on peut chercher plus
         profondement dans le meme temps.
       - Reference historique de l'algorithme : Knuth, D.E. & Moore, R.W.
         (1975). "An analysis of alpha-beta pruning". Artificial
         Intelligence, 6(4), 293-326.
       - Le sujet du projet recommande lui-meme cette approche pour un
         "niveau standard" et precise que ce type d'agent a remporte le
         concours plusieurs sessions (voir section 9 du sujet).

    2) Profondeur de recherche : fixee a 2 demi-coups pour cette V1.
       - Le nombre de coups possibles a chaque tour est tres grand des
         qu'on autorise les murs (jusqu'a 2*8*8 = 128 placements de mur
         possibles en plus des deplacements), donc l'arbre explose vite.
       - Une V1 doit avant tout FONCTIONNER et etre soumise a temps
         (echeance V1). Une profondeur 2 se calcule en une fraction de
         seconde et donne deja un agent qui bat un joueur aleatoire/glouton
         dans la plupart des cas, car il "voit" une reponse de l'adversaire.
       - Reference : Mertens, P.J.C. (2006). "A Quoridor-playing Agent"
         (memoire, Universite de Maastricht) - utilise precisement minimax
         + alpha-beta avec une profondeur de recherche de 2 dans ses
         experiences, pour les memes raisons de complexite de l'arbre.
         https://project.dke.maastrichtuniversity.nl/games/files/bsc/Mertens_BSc-paper.pdf
       - Piste d'amelioration pour V2/V3 (a mentionner dans le rapport
         comme "evolution de l'agent") : approfondissement iteratif
         (iterative deepening) pour exploiter tout le budget de 15 minutes
         au lieu d'une profondeur fixe.

    3) Heuristique : difference de plus court chemin vers la ligne d'arrivee.
           h(etat) = distance(adversaire) - distance(moi)
       - Plus mon chemin restant est court par rapport a celui de
         l'adversaire, meilleur est l'etat pour moi : cette heuristique
         encode directement l'objectif du jeu (etre le premier arrive).
       - C'est l'heuristique la plus citee dans la litterature sur Quoridor
         (Mertens, 2006 ; agents "greedy" classiques) et c'est exactement
         celle utilisee par l'agent glouton fourni avec le projet
         (greedy_player_quoridor.py), qui appelle deja
         `state._shortest_path(player)`.
       - Pourquoi reutiliser `GameStateQuoridor._shortest_path` plutot que
         recoder un BFS a la main : cette methode est deja fournie,
         testee et utilisee par le code officiel du cours (notamment pour
         valider qu'un mur ne bloque pas totalement un joueur, voir
         `_is_wall_legal`). La reimplementer soi-meme ajouterait un risque
         de bug sans rien apporter pour une V1.
       - LIMITE CONNUE (a mentionner dans le rapport comme piste
         d'amelioration) : cette methode ignore le pion adverse pendant le
         calcul du chemin (elle suppose qu'on peut "traverser" la case de
         l'adversaire). Le vrai plus court chemin en tenant compte des
         sauts serait plus precis mais plus couteux a calculer a chaque
         noeud de l'arbre - a envisager pour une version ulterieure si le
         temps de calcul le permet.

    Attributes:
        piece_type (str): piece type of the player
    """

    # Profondeur fixe pour cette V1 (voir justification ci-dessus).
    DEPTH = 2

    # Temps (en secondes) qu'on s'autorise a utiliser pour UN SEUL appel de
    # compute_action. Tres prudent pour la V1 : le budget total est de
    # 15 minutes pour toute la partie (voir section 2 du sujet), donc on
    # ne veut surtout pas tout depenser sur un seul coup. Les versions
    # suivantes repartiront ce budget plus intelligemment.
    TIME_BUDGET = 5.0

    def __init__(self, piece_type: str, goal_row: int = 0, name: str = "bob", *args, **kwargs) -> None:
        """
        Initialize the PlayerQuoridor instance.

        Args:
            piece_type (str): Type of the player's game piece
            goal_row (int): The row the player wants to reach
            name (str, optional): Name of the player (default is "bob")
        """
        super().__init__(piece_type, goal_row, name)

    # ------------------------------------------------------------------
    # Point d'entree demande par le framework
    # ------------------------------------------------------------------
    def compute_action(self, current_state: GameStateQuoridor, remaining_time: float = 15 * 60, **kwargs) -> Action:
        """
        Use the minimax algorithm to choose the best action based on the heuristic evaluation of game states.

        Args:
            current_state (GameStateQuoridor): The current game state.

        Returns:
            Action: The best action as determined by minimax.
        """
        start_time = time.time()

        # generate_possible_stateless_actions() est un GENERATEUR (voir
        # game_state_quoridor.py) : on le transforme en liste une seule
        # fois pour pouvoir le parcourir et connaitre sa longueur.
        actions = list(current_state.generate_possible_stateless_actions())

        if not actions:
            # Ne devrait pas arriver si la partie n'est pas terminee, mais
            # on evite un crash silencieux si jamais c'est le cas.
            raise RuntimeError("Aucune action legale disponible.")

        if len(actions) == 1:
            return actions[0]

        best_action = actions[0]     # valeur de repli si on manque de temps
        best_value = float("-inf")
        alpha, beta = float("-inf"), float("inf")

        # Niveau racine : c'est TOUJOURS mon tour ici (je suis l'active_player
        # de current_state), donc on est en train de MAXIMISER. Chaque action
        # testee mene a un etat ou c'est au tour de l'adversaire -> l'appel
        # recursif se fait avec maximizing=False.
        for action in actions:
            if time.time() - start_time > self.TIME_BUDGET:
                break

            child_state = current_state.apply_action(action)
            value = self._alphabeta(child_state, self.DEPTH - 1, alpha, beta, maximizing=False)

            if value > best_value:
                best_value = value
                best_action = action

            alpha = max(alpha, best_value)

        return best_action

    # ------------------------------------------------------------------
    # Minimax + alpha-beta
    # ------------------------------------------------------------------
    def _alphabeta(self, state: GameStateQuoridor, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
        """
        Explore recursivement l'arbre de jeu avec elagage alpha-beta.

        Pourquoi on sait "de quel cote on est" (maximizing) sans avoir a
        comparer active_player.id a chaque niveau : a Quoridor, un tour =
        une action, les joueurs alternent STRICTEMENT (voir apply_action,
        qui appelle toujours compute_next_player()). Donc si le niveau
        racine (profondeur DEPTH) correspond a mon tour, le niveau suivant
        correspond forcement au tour de l'adversaire, etc. La parite de la
        profondeur suffit, pas besoin d'interroger state.active_player ici.

        alpha : la meilleure valeur que MOI (le joueur MAX) puis garantir
                sur ce chemin jusqu'ici.
        beta  : la meilleure valeur que L'ADVERSAIRE (le joueur MIN) peut
                garantir sur ce chemin jusqu'ici.
        Si a un moment alpha >= beta, l'adversaire (ou moi) ne choisira
        jamais cette branche -> on peut arreter de l'explorer (coupure).
        """
        if depth == 0 or state.is_done():
            return self._evaluate(state)

        actions = state.generate_possible_stateless_actions()

        if maximizing:
            value = float("-inf")
            for action in actions:
                child = state.apply_action(action)
                value = max(value, self._alphabeta(child, depth - 1, alpha, beta, False))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break  # coupure beta : l'adversaire a deja mieux ailleurs
            return value
        else:
            value = float("inf")
            for action in actions:
                child = state.apply_action(action)
                value = min(value, self._alphabeta(child, depth - 1, alpha, beta, True))
                beta = min(beta, value)
                if alpha >= beta:
                    break  # coupure alpha : je fais deja mieux ailleurs
            return value

    # ------------------------------------------------------------------
    # Heuristique
    # ------------------------------------------------------------------
    def _evaluate(self, state: GameStateQuoridor) -> float:
        """
        Evalue un etat du point de vue de MOI (self), independamment de
        qui est actuellement `active_player` dans `state`.

        h(state) = distance_plus_courte(adversaire) - distance_plus_courte(moi)

        -> positif si je suis plus proche du but que l'adversaire (bon
           pour moi), negatif sinon.

        Cas particulier : si la partie est terminee (state.is_done() est
        vrai), on retourne une valeur extreme plutot que la simple
        difference de distance, pour etre certain qu'une victoire/defaite
        avere l'emporte toujours sur n'importe quelle autre consideration
        heuristique dans la comparaison minimax.
        """
        my_id = self.get_id()
        me = next(p for p in state.players if p.get_id() == my_id)
        opponent = next(p for p in state.players if p.get_id() != my_id)

        if state.is_done():
            if state.scores[me.id] == 1.0:
                return float("inf")
            if state.scores[opponent.id] == 1.0:
                return float("-inf")

        # _shortest_path est une methode "privee" (prefixee par _) de
        # GameStateQuoridor, deja fournie et utilisee par
        # greedy_player_quoridor.py. On peut tout a fait l'appeler depuis
        # notre propre classe : en Python, le prefixe _ est une convention
        # ("usage interne recommande") et non une veritable restriction
        # d'acces comme dans d'autres langages.
        my_distance = state._shortest_path(me)
        opponent_distance = state._shortest_path(opponent)

        return float(opponent_distance - my_distance)