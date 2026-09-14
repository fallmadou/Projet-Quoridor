import time
from player_quoridor import PlayerQuoridor
from seahorse.game.action import Action
from game_state_quoridor import GameStateQuoridor
from seahorse.utils.custom_exceptions import MethodNotImplementedError


class MyPlayer(PlayerQuoridor):
    """
    Player class for Quoridor game.

    Attributes:
        piece_type (str): piece type of the player
    """

    # Profondeur fixe pour cette V1 (voir justification ci-dessus).
    DEPTH = 2

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

        actions = list(current_state.generate_possible_stateless_actions())

        if not actions:
            
            raise RuntimeError("Aucune action legale disponible.")

        if len(actions) == 1:
            return actions[0]

        best_action = actions[0]     # valeur de repli si on manque de temps
        best_value = float("-inf")
        alpha, beta = float("-inf"), float("inf")


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

        my_id = self.get_id()
        me = next(p for p in state.players if p.get_id() == my_id)
        opponent = next(p for p in state.players if p.get_id() != my_id)

        if state.is_done():
            if state.scores[me.id] == 1.0:
                return float("inf")
            if state.scores[opponent.id] == 1.0:
                return float("-inf")

        my_distance = state._shortest_path(me)
        opponent_distance = state._shortest_path(opponent)

        return float(opponent_distance - my_distance)
