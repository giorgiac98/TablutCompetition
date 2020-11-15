package it.unibo.ai.didattica.competition.tablut.util;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Random;

import it.unibo.ai.didattica.competition.tablut.domain.State;

public class Node<T> {
	
	private T data;
	private int visitCount;
	private double winScore;
	private Node<T> parent;
	private List<Node<T>> children;
	
	public Node(T data) {
		this(data, null);
	}
	
	public Node(T data, Node<T> parent) {
		this.data = data;
		this.visitCount = 0;
		this.winScore = 0;
		this.parent = parent;
		this.children = new ArrayList<>();
	}
	
	public Node(Node<T> toCopy) {
		this.data = toCopy.getData();
		this.parent = toCopy.getParent();
		this.children = toCopy.getChildren();
		this.visitCount = toCopy.getVisitCount();
		this.winScore = toCopy.getWinScore();
	}
	
	public T getData() {
		return data;
	}
	
	public Node<T> getParent() {
		return parent;
	} 
	
	public List<Node<T>> getChildren() {
		return children;
	}
	
	@SuppressWarnings("unchecked")
	public void addChildren(Node<T>... children) {
		this.children.addAll(Arrays.asList(children));
	}
	
	public int getVisitCount() {
		return this.visitCount;
	}
	
	public void incrementVisit() {
		this.visitCount++;
	}
	
	public double getWinScore() {
		return winScore;
	}
	
	public void setWinScore(int minValue) {
		this.winScore = minValue;
	}
	
	public void addScore(double scoreToAdd) {
		this.winScore += scoreToAdd;
	}

	public Node<T> getRandomChildNode() {
		int i = new Random().nextInt(this.children.size() - 1);
		return this.children.get(i);
	}

	public Node<T> getChildWithMaxScore() {
		return Collections.max(this.children, 
				(c1, c2) -> Double.valueOf(c1.getWinScore()).compareTo(c2.getWinScore()));
	}
}