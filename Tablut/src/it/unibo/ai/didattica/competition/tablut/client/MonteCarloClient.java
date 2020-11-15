package it.unibo.ai.didattica.competition.tablut.client;

import java.io.IOException;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.List;

import it.unibo.ai.didattica.competition.tablut.domain.Action;
import it.unibo.ai.didattica.competition.tablut.domain.GameAshtonTablut;
import it.unibo.ai.didattica.competition.tablut.domain.State;
import it.unibo.ai.didattica.competition.tablut.domain.State.Pawn;
import it.unibo.ai.didattica.competition.tablut.domain.State.Turn;
import it.unibo.ai.didattica.competition.tablut.domain.StateTablut;
import it.unibo.ai.didattica.competition.tablut.exceptions.ActionException;
import it.unibo.ai.didattica.competition.tablut.exceptions.BoardException;
import it.unibo.ai.didattica.competition.tablut.exceptions.CitadelException;
import it.unibo.ai.didattica.competition.tablut.exceptions.ClimbingCitadelException;
import it.unibo.ai.didattica.competition.tablut.exceptions.ClimbingException;
import it.unibo.ai.didattica.competition.tablut.exceptions.DiagonalException;
import it.unibo.ai.didattica.competition.tablut.exceptions.OccupitedException;
import it.unibo.ai.didattica.competition.tablut.exceptions.PawnException;
import it.unibo.ai.didattica.competition.tablut.exceptions.StopException;
import it.unibo.ai.didattica.competition.tablut.exceptions.ThroneException;
import it.unibo.ai.didattica.competition.tablut.util.Coordinate;
import it.unibo.ai.didattica.competition.tablut.util.Node;
import it.unibo.ai.didattica.competition.tablut.util.SearchTree;
import it.unibo.ai.didattica.competition.tablut.util.UCT;

public class MonteCarloClient extends TablutClient{
	
	private List <Coordinate> citadels = new ArrayList<>(16);
	private List<Coordinate> whiteCheckers = new ArrayList<>(8);
	private List<Coordinate> blackCheckers = new ArrayList<>(16);
	private Coordinate king;
	private int boardDimension;
	private Turn opponent;
	private GameAshtonTablut rules;
	
	public MonteCarloClient(String player) throws UnknownHostException, IOException {
		super(player, "MonteCarloSearchTree");
	}
	

	public static void main(String[] args) throws UnknownHostException, IOException {
		String role = "";

		if (args.length < 1) {
			System.out.println("You must specify which player you are (WHITE or BLACK)");
			System.exit(-1);
		} else {
			System.out.println(args[0]);
			role = (args[0]);
		}
		System.out.println("Selected client: " + args[0]);

		MonteCarloClient client = new MonteCarloClient(role);
		client.run();
	}

	@Override
	public void run() {
		try {
			this.declareName();
		} catch (Exception e) {
			e.printStackTrace();
		}
		
		State state = new StateTablut();
		state.setTurn(State.Turn.WHITE);
		this.rules = new GameAshtonTablut(99, 0, "garbage", "fake", "fake");
		System.out.println("Ashton Tablut game");
		
		// Popolo i miei riferimenti
		this.opponent = this.getPlayer() == Turn.BLACK? Turn.WHITE : Turn.BLACK;
		Pawn[][] b = state.getBoard();
		this.boardDimension = b.length; // strong assumption of a square board
		for(int i = 0; i < b.length; i++) {
			for(int j = 0; j < b[i].length; j++) {
				if(b[i][j].equals(State.Pawn.BLACK)) {
					blackCheckers.add(new Coordinate(i, j));
					citadels.add(new Coordinate(i, j));
				}else if(b[i][j].equals(State.Pawn.WHITE)) {
					whiteCheckers.add(new Coordinate(i, j));
				}else if(b[i][j].equals(State.Pawn.KING)) {
					this.king = new Coordinate(i, j);
				}
			}
		}
		
		while(state.getTurn().equals(Turn.BLACK) || state.getTurn().equals(Turn.WHITE)) { // game not ended
			try {
				this.read();
			} catch (ClassNotFoundException | IOException e1) {
				// TODO Auto-generated catch block
				e1.printStackTrace();
				System.exit(1);
			}
			System.out.println("Current state:");
			state = this.getCurrentState();
			System.out.println(state.toString());
			try {// needed??
				Thread.sleep(1000);
			} catch (InterruptedException e) {
				
			}
			
			// check any checker has been captured
			this.blackCheckers.removeIf(c -> this.getCurrentState().getPawn(c.getX(), c.getY()).equals(Pawn.EMPTY));
			this.whiteCheckers.removeIf(c -> this.getCurrentState().getPawn(c.getX(), c.getY()).equals(Pawn.EMPTY));
			
			// compute move
			Action chosen = findNextMove(state);
//			
			
			System.out.println("Mossa scelta: " + chosen.toString());
			try {
				this.write(chosen);
			} catch (ClassNotFoundException | IOException e) {
				e.printStackTrace();
			}
		}
		
		// game ended
		System.out.println("End of the game");
		System.out.println(state.toString());
	}
	
	private Action findNextMove(State state) {
		long end = System.currentTimeMillis() + 30000;
		
		SearchTree<State> gameTree = new SearchTree<>(this.getCurrentState().clone());
		Node<State> rootNode = gameTree.getRoot();
		List<Action> actions = null;
		
		while (System.currentTimeMillis() < end) {
			Node<State> promisingNode = selectPromisingNode(rootNode);
			if(promisingNode.getData().getTurn().equals(Turn.BLACK) || promisingNode.getData().getTurn().equals(Turn.WHITE)) {
				actions = expandNode(promisingNode);
			}
            Node<State> nodeToExplore = promisingNode;
            if (promisingNode.getChildren().size() > 0) {
                nodeToExplore = promisingNode.getRandomChildNode();
            }
            int playoutResult = simulateRandomPlayout(nodeToExplore);
            backPropogation(nodeToExplore, playoutResult);
		}
		
		Node<State> winnerNode = rootNode.getChildWithMaxScore();
		int i = rootNode.getChildren().indexOf(winnerNode);
        return actions == null ? null : actions.get(i);
	}
	
	private Node<State> selectPromisingNode(Node<State> rootNode) {
		Node<State> node = rootNode;
	    while (node.getChildren().size() != 0) {
	        node = UCT.findBestNodeWithUCT(node);
	    }
	    return node;
	}
	
	private List<Action> expandNode(Node<State> promisingNode) {
		List<Action> allActions = this.generateMoves(this.getPlayer(), promisingNode.getData());
		List<Action> validActions = new ArrayList<>();
		for (Action a : allActions) {
			State afterAction = null;
			try {
				afterAction = this.rules.checkMove(promisingNode.getData(), a);
			} catch (BoardException | ActionException | StopException | PawnException | DiagonalException
					| ClimbingException | ThroneException | OccupitedException | ClimbingCitadelException
					| CitadelException e) {
				// move not valid
			}
			if(afterAction != null) {
				validActions.add(a);
				// the state after the valid action is added to the children of the node
				promisingNode.addChildren(new Node<>(afterAction, promisingNode));
			}
		}
		return validActions;
	}
	
	private Turn simulateRandomPlayout(Node<State> node) {
		Node<State> tempNode = new Node<State>(node);
	    State tempState = tempNode.getData();
	    Turn boardStatus = tempState.getTurn();
	    if (this.opponent == ) {
	        tempNode.getParent().setWinScore(Integer.MIN_VALUE);
	        return boardStatus;
	    }
	    while (boardStatus == Board.IN_PROGRESS) {
	        tempState.togglePlayer();
	        tempState.randomPlay();
	        boardStatus = tempState.getBoard().checkStatus();
	    }
	    return boardStatus;
	}
	
	private void backPropogation(Node<State> nodeToExplore, Turn player) {
		Node<State> tempNode = nodeToExplore;
	    while (tempNode != null) {
	        tempNode.incrementVisit();
	        if (tempNode.getData().getTurn().equals(player)) {
	            tempNode.getState().addScore(WIN_SCORE);
	        }
	        tempNode = tempNode.getParent();
		
	}

	private List<Action> generateMoves(Turn player, State state) {
		List<Action> result = null;
		if(player.equals(Turn.BLACK)) {
			for(Coordinate b : this.blackCheckers) {
				try {
					result = compute(player, b, state);
				} catch (IOException e) {
					e.printStackTrace();
				}
			}
		} else {
			for(Coordinate w : this.whiteCheckers) {
				try {
					result = compute(player, w, state);
				} catch (IOException e) {
					e.printStackTrace();
				}
			}	
			try {
				result.addAll(compute(player, this.king, state));
			} catch (IOException e) {
				e.printStackTrace();
			}
		}
		return result;
	}
	
	private List<Action> compute(Turn player, Coordinate c, State state) throws IOException {
		ArrayList<Action> result = new ArrayList<>();
		// UP
		int i = c.getX() - 1;
		Coordinate to = new Coordinate(i, c.getY());
		while(i >= 0 && isLegitimate(to, state)) {
			result.add(new Action(c.toString(), to.toString(), player));
			to.up();
			i--;
		}
		// DOWN
		i = c.getX() + 1;
		to = new Coordinate(i, c.getY());
		while(i < this.boardDimension && isLegitimate(to, state)) {
			result.add(new Action(c.toString(), to.toString(), player));
			to.down();
			i++;
		}
		// LEFT
		i = c.getY() - 1;
		to = new Coordinate(c.getX() , i);
		while(i >= 0 && isLegitimate(to, state)) {
			result.add(new Action(c.toString(), to.toString(), player));
			to.left();
			i--;
		}
		// RIGHT
		i = c.getY() + 1;
		to = new Coordinate(c.getX() , i);
		while(i < this.boardDimension && isLegitimate(to, state)) {
			result.add(new Action(c.toString(), to.toString(), player));
			to.right();
			i++;
		}
		return result;
	}
	
	private boolean isLegitimate(Coordinate to, State state) {
		Pawn cell = state.getPawn(to.getX(), to.getY());
		if(state.getTurn().equals(Turn.WHITE)) {
			return cell.equals(Pawn.EMPTY) && !this.citadels.contains(to); 
		}
		return cell.equals(Pawn.EMPTY); 
	}
}
