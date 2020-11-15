package it.unibo.ai.didattica.competition.tablut.util;

public class SearchTree<T> {	
	
	static final double WIN_SCORE = 3;
	static final double DRAW_SCORE = 1;
	
	private Node<T> root;
	
	public SearchTree(T gameState) {
		this.root = new Node<>(gameState);
	}
	
	public Node<T> getRoot() {
		return root;
	}
}
