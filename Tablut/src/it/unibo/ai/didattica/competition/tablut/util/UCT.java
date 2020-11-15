package it.unibo.ai.didattica.competition.tablut.util;

import java.util.Collections;
import java.util.Comparator;

import it.unibo.ai.didattica.competition.tablut.domain.State;

public class UCT {
	
    public static double uctValue(int totalVisit, double nodeWinScore, int nodeVisit) {
        if (nodeVisit == 0) {
            return Integer.MAX_VALUE;
        }
        return ((double) nodeWinScore / (double) nodeVisit) 
          + 1.41 * Math.sqrt(Math.log(totalVisit) / (double) nodeVisit);
    }
 
    public static Node<State> findBestNodeWithUCT(Node<State> node) {
        int parentVisit = node.getVisitCount();
        return Collections.max(
          node.getChildren(),
          Comparator.comparing(c -> uctValue(parentVisit, 
            c.getWinScore(), c.getVisitCount())));
    }
}