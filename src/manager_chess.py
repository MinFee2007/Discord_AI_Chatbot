import chess, math, time
import chess.svg
import io

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0
}
PAWN_PST:list[list[int]] = [
    [0,0,0,0,0,0,0,0],
    [50,50,50,50,50,50,50,50],
    [10,10,20,30,30,20,10,10],
    [5,5,10,25,25,10,5,5],
    [0,0,0,20,20,0,0,0],
    [5,-5,-10,0,0,-10,-5,5],
    [5,10,10,-20,-20,10,10,5],
    [0,0,0,0,0,0,0,0]
]
KNIGHT_PST:list[list[int]] = [
    [-20,-10,-10,-10,-10,-10,-10,-20],
    [-10,-5,-5,-5,-5,-5,-5,-10],
    [-10,-5,15,15,15,15,-5,-10],
    [-10,-5,15,20,20,15,-5,-10],
    [-10,-5,15,20,20,15,-5,-10],
    [-10,-5,15,15,15,15,-5,-10],
    [-10,-5,-5,-5,-5,-5,-5,-10],
    [-20,-10,-10,-10,-10,-10,-10,-20]
]
BISHOP_PST:list[list[int]] = [
    [-20,-10,-10,-10,-10,-10,-10,-20],
    [-10,0,0,0,0,0,0,-10],
    [-10,0,5,10,10,5,0,-10],
    [-10,5,5,10,10,5,5,-10],
    [-10,0,10,10,10,10,0,-10],
    [-10,10,10,10,10,10,10,-10],
    [-10,5,0,0,0,0,5,-10],
    [-20,-10,-10,-10,-10,-10,-10,-20]
]
ROOK_PST:list[list[int]] = [
    [0,0,0,0,0,0,0,0],
    [5,10,10,10,10,10,10,5],
    [-5,0,0,0,0,0,0,-5],
    [-5,0,0,0,0,0,0,-5],
    [-5,0,0,0,0,0,0,-5],
    [-5,0,0,0,0,0,0,-5],
    [-5,0,0,0,0,0,0,-5],
    [0,0,0,5,5,0,0,0]
]
QUEEN_PST:list[list[int]] = [
    [-20,-10,-10,-5,-5,-10,-10,-20],
    [-10,0,0,0,0,0,0,-10],
    [-10,0,5,5,5,5,0,-10],
    [-5,0,5,5,5,5,0,-5],
    [0,0,5,5,5,5,0,-5],
    [-10,5,5,5,5,5,0,-10],
    [-10,0,5,0,0,0,0,-10],
    [-20,-10,-10,-5,-5,-10,-10,-20]
]
KING_MG_PST:list[list[int]] = [
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-20,-30,-30,-40,-40,-30,-30,-20],
    [-10,-20,-20,-20,-20,-20,-20,-10],
    [20,20,0,0,0,0,20,20],
    [20,30,10,0,0,10,30,20]
]
KING_EG_PST:list[list[int]] = [
    [-50,-40,-30,-20,-20,-30,-40,-50],
    [-30,-20,-10,0,0,-10,-20,-30],
    [-30,-10,20,30,30,20,-10,-30],
    [-30,-10,30,40,40,30,-10,-30],
    [-30,-10,30,40,40,30,-10,-30],
    [-30,-10,20,30,30,20,-10,-30],
    [-30,-30,0,0,0,0,-30,-30],
    [-50,-30,-30,-30,-30,-30,-30,-50]
]

class ChessManager:
    def __init__(self):
        self.board = chess.Board()

    def render_board_image(self, last_move: chess.Move | None = None, flipped: bool = False) -> io.BytesIO:
        """Render the current board state into PNG bytes stream to send onto Discord"""
        import cairosvg
        svg_data = chess.svg.board(
            board=self.board,
            lastmove=last_move,
            flipped=flipped, # True if the player is playing as black side
            size=400
        )
        png_bytes = cairosvg.svg2png(bytestring=svg_data.encode("utf-8"))
        return io.BytesIO(png_bytes)
    
    def create_board(self):
        """Create a casual chess board"""
        self.board = chess.Board()
        return self.board
    
    def fen_to_board(self, board:chess.Board|None, fen:str):
        """Return a board set up using FEN string"""
        if board:
            board.set_fen(fen)
            return
        self.board = chess.Board(fen)
        return self.board

    def board_to_fen(self, board:chess.Board|None):
        """Return the state of the board in FEN format"""
        if board:
            return board.fen()
        return self.board.fen()
    
    def get_legal_moves(self):
        return list(self.board.legal_moves)

    def is_checkmate(self):
        return self.board.is_checkmate()

    def is_stalemate(self):
        return self.board.is_stalemate()

    def get_outcome(self) -> chess.Outcome:
        return self.board.outcome()

    def get_last_move(self, board:chess.Board|None=None) -> chess.Move:
        """Get the last move on the board"""
        try:
            if board:
                last_move: chess.Move = board.peek()
            else:
                last_move: chess.Move = self.board.peek()
            return last_move
        except IndexError:
            return None

    def make_move(self,move_str:str):
        """Make a chess move on the board, process the move in SAN format first then UCI"""
        move_str = move_str.strip()
        try:
            move = self.board.parse_san(move_str)
        except ValueError:
            move = chess.Move.from_uci(move_str.lower())
        if move in self.board.legal_moves:
            self.board.push(move)
            return move
        raise ValueError(f"Illegal move: {move_str}")

    def is_terminal(self, board_state:chess.Board | None = None):
        """Return True on terminal board state, else return False"""
        if board_state is None:
            board_state = self.board
        return board_state.is_game_over()

    def get_pst_score(self, piece:chess.Piece, col:int, row:int, is_white:bool, is_end_game:bool) -> int:
        """Get score of a piece based on its piece-square table (PST)"""
        # "Rotate the board" if it is black turn
        if not is_white:
            row = 7 - row

        if piece.piece_type == chess.PAWN:
            return PAWN_PST[row][col]
        elif piece.piece_type == chess.KNIGHT:
            return KNIGHT_PST[row][col]
        elif piece.piece_type == chess.BISHOP:
            return BISHOP_PST[row][col]
        elif piece.piece_type == chess.ROOK:
            return ROOK_PST[row][col]
        elif piece.piece_type == chess.QUEEN:
            return QUEEN_PST[row][col]
        elif piece.piece_type == chess.KING:
            if is_end_game:
                return KING_EG_PST[row][col]
            else:
                return KING_MG_PST[row][col]

    def evaluate(self, board_state:chess.Board):
        """
        Utility function for Minimax + Alpha-Beta Pruning
        Positive score favors WHITE, negative score favors BLACK
        """
        if board_state.is_checkmate():
            return -100000.0 if board_state.turn == chess.WHITE else 100000.0
        if board_state.is_game_over():
            return 0.0
        is_end_game = (len(board_state.pieces(chess.QUEEN, chess.WHITE)) == 0 and len(board_state.pieces(chess.QUEEN, chess.BLACK)) == 0)
        score = 0

        for square_index, piece in board_state.piece_map().items():
            row = 7 - (square_index // 8)
            col = square_index % 8
            if not piece:
                continue
            if piece.color == chess.WHITE: # Maximizing player
                score += (PIECE_VALUES[piece.piece_type] + self.get_pst_score(piece,col,row,True,is_end_game))
            else:
                score -= (PIECE_VALUES[piece.piece_type] + self.get_pst_score(piece,col,row,False,is_end_game))
        
        return score

    def alpha_beta(self, board_state:chess.Board, depth=4, alpha=-math.inf, beta=math.inf, maximizing_player=True, end_time_ns:int=-1):
        """Minimax + Alpha-Beta Pruning for finding the best move"""
        if end_time_ns != -1 and end_time_ns <= time.perf_counter_ns():
            raise TimeoutError()

        if depth == 0 or self.is_terminal(board_state):
            return self.evaluate(board_state), None

        if maximizing_player:
            max_score = -math.inf
            best_move: chess.Move = None
            for next_move in board_state.legal_moves:
                board_state.push(next_move)
                score, _ = self.alpha_beta(board_state, depth-1, alpha, beta, False, end_time_ns)
                board_state.pop()
                if score > max_score:
                    max_score = score
                    alpha = max(alpha, score)
                    best_move = next_move
                if alpha >= beta:
                    break
            return max_score, best_move
        else:
            min_score = math.inf
            best_move: chess.Move = None
            for next_move in board_state.legal_moves:
                board_state.push(next_move)
                score, _ = self.alpha_beta(board_state, depth-1, alpha, beta, True, end_time_ns)
                board_state.pop()
                if score < min_score:
                    min_score = score
                    beta = min(beta, score)
                    best_move = next_move
                if alpha >= beta:
                    break
            return min_score, best_move

    def get_best_move(self, time_limit_ns:int, top_k:int=3) -> list[tuple[chess.Move, float]]:
        """Get best move for the next turn using iterative deepening with a limit of thinking time"""
        board_state = self.board.copy()
        if self.is_terminal(board_state): return []
        max_depth = 10
        is_white_turn = (board_state.turn == chess.WHITE)
        end_time = time.perf_counter_ns() + time_limit_ns

        ordered_moves = list(board_state.legal_moves)
        best_top_moves: list[tuple[chess.Move, float]] = []

        for depth in range(1, max_depth+1):
            current_scored_moves: list[tuple[chess.Move, float]] = []
            alpha = -math.inf
            beta = math.inf

            try:
                for move in ordered_moves:
                    board_state.push(move)
                    score, _ = self.alpha_beta(board_state, depth-1, alpha, beta, not is_white_turn, end_time)
                    board_state.pop()
                    current_scored_moves.append((move, score))

                    if len(current_scored_moves) >= top_k:
                        current_scored_moves.sort(key=lambda x:x[1], reverse=is_white_turn)
                        kth_score = current_scored_moves[top_k-1][1]
                        if is_white_turn:
                            alpha = max(alpha,kth_score)
                        else:
                            beta = min(beta,kth_score)

                current_scored_moves.sort(key=lambda x: x[1], reverse=is_white_turn)
                best_top_moves = current_scored_moves[:top_k]
                ordered_moves = [m for m,_ in current_scored_moves]

            except TimeoutError:
                break

        return best_top_moves