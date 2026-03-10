import utils
import P_L
import P_R
import C_c

def E_s(game, player):

    Delta_C_T = 0
    for p in game.players:
        if not p.name == player.name: # Compare name, player obj is not comparable
            Delta_C_T += claimed_route_points(game.graph, p)

    Evaluation = Delta_C_T
               + P_L.P_L(game, player) * game.longest_route_points
               + P_R.P_R(game, player) * player.route.points
               + C_C.C_c(game, player)

    return Evaluation