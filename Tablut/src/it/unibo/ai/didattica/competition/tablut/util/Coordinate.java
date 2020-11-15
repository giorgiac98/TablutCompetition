package mcts;

public class Coordinate {

	private int x;
	private int y;
	
	
	public Coordinate(int x, int y) {
		this.x = x;
		this.y = y;
	}
	
	public int getX() {
		return this.x;
	}
	
	public int getY() {
		return this.y;
	}
	
	public void up() {
		this.x--; 
	}
	
	public void down() {
		this.x++;
	}
	
	public void left() {
		this.y--;
	}
	
	public void right() {
		this.y++;
	}
	
	@Override
	public String toString() {
		String ret;
		char col = (char) (this.y + 97);
		ret = col + "" + (this.x + 1);
		return ret;
	}
}
