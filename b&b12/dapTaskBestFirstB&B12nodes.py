import sys

from docplex.cp.utils import xrange

sys.path.append(r'C:\Program Files\IBM\ILOG\CPLEX_Studio_Community2211\cplex\python\3.10\x64_win64')

try:
    import cplex
    from cplex import Cplex
except ImportError as e:
    print(f"Błąd importu CPLEX: {e}")
    exit()

import numpy as np

from amplpy import AMPL, add_to_path

add_to_path(r"C:\Users\jakub\Desktop\AMPL\AMPL")


def addNewConstraint(ampl, demand, path, value):
    new_constraint = f"""
            subject to limitPath_{demand}_{path} :
                u[{demand}, {path}] = {value:.1f};
            """

    ampl.eval(new_constraint)


def addLimitPathConstraint(ampl, limit):
    new_constraint = f"""
       subject to max_two_paths_per_demand {{demand in Demands}}:
        sum {{demandPath in 1..demand_maxPath[demand]}} u[demand, demandPath] <= {limit};
       """

    ampl.eval(new_constraint)


def solve_cplex(c, bounds, addLimitPath):
    # try:

    ampl = AMPL()

    ampl.set_option("solver_msg", "off")

    ampl.read("newDap.mod")

    ampl.read_data("net12New2.txt")


    addLimitPathConstraint(ampl, pathLimit if addLimitPath else 1) #to mozna odrazu w ampl

    for i in xrange(0, len(bounds)):
        if bounds[i] == (0, 0):
            print("zmiana na 0  dla demand/path", c[i][0], c[i][1])
            addNewConstraint(ampl, c[i][0], c[i][1], 0)
        elif bounds[i] == (1, 1):
            print("zmiana na 1  dla demand/path", c[i][0], c[i][1])
            addNewConstraint(ampl, c[i][0], c[i][1], 1)

    ampl.option["solver"] = "cplex"
    ampl.solve()


    valuesList = []
    udpList = []

    solve_status = ampl.get_data("solve_message").to_list()  # Jeśli dostępne
    if "no feasible solution" in solve_status[0].lower():
        print("Brak wykonalnego rozwiązania. Sprawdź dane wejściowe lub ograniczenia.")
        z = "infeasible"
        return udpList, valuesList, z


    solution = ampl.getVariable("pathDemand_volumeCount").getValues().to_dict()

    udp = ampl.getVariable("u").getValues().to_dict()

    for key in solution.keys():
        valuesList.append(solution.get(key))

    for key in udp.keys():
        udpList.append(udp.get(key))
    print(udpList)

    z = ampl.getVariable("z").getValues().to_list()

    return udpList, valuesList, z[0]

import heapq


def branch_and_bound_best_first(c):
    z_best = float('+inf')
    x_best = None
    element_list = []

    NU = list(range(len(c)))
    N0, N1 = [], []
    bounds = [(0, 1) for _ in range(len(c))]
    udp, x, z = solve_cplex(c, bounds, False)  # Rozwiązanie początkowe

    if x is not None:
        heapq.heappush(element_list, (-z, NU, N0, N1, np.array(x), udp))  # -z bo heapq to min-heap

    counter = 1
    while element_list:
        _, NU, N0, N1, x, udp = heapq.heappop(element_list)

        if z == "infeasible":
            continue

        if not NU or all(np.isclose(udp[i], round(udp[i])) for i in NU):
            if z < z_best:
                z_best = z
                x_best = x
                u_best = udp
            continue

        if z >= z_best:
            continue

        print(f"Węzeł {counter}: Z = {z}")
        counter += 1

        # Wybieramy pierwszą zmienną z wartością ułamkową
        fractional_index = [i for i in NU if not np.isclose(udp[i], 0) and not np.isclose(udp[i], 1)][0]

        # Gałąź 1: xi = 1
        new_NU_1 = [v for v in NU if v != fractional_index]
        new_N1 = N1 + [fractional_index]
        bounds_1 = [(0, 1) for _ in range(len(c))]
        for idx in N0:
            bounds_1[idx] = (0, 0)
        for idx in new_N1:
            bounds_1[idx] = (1, 1)
        udp_1, x_1, z_1 = solve_cplex(c, bounds_1, True)
        if x_1 is not None and z_1 != "infeasible":
            heapq.heappush(element_list, (-z_1, new_NU_1, N0, new_N1, np.array(x_1), udp_1))

        # Gałąź 2: xi = 0
        new_NU_0 = [v for v in NU if v != fractional_index]
        new_N0 = N0 + [fractional_index]
        bounds_0 = [(0, 1) for _ in range(len(c))]
        for idx in new_N0:
            bounds_0[idx] = (0, 0)
        for idx in N1:
            bounds_0[idx] = (1, 1)
        udp_2, x_0, z_0 = solve_cplex(c, bounds_0, True)
        if x_0 is not None and z_0 != "infeasible":
            heapq.heappush(element_list, (-z_0, new_NU_0, new_N0, N1, np.array(x_0), udp_2))

    print(u_best)
    return x_best, z_best


if __name__ == "__main__":
    # c ponizej dla pliku net12New.txt
    # c = [[1, 1], [1, 2], [1, 3], [1, 4], [2, 1], [2, 2], [2, 3], [2, 4], [3, 1], [3, 2], [3, 3], [3, 4], [3, 5], [3, 6],
    #      [4, 1], [4, 2], [4, 3], [4, 4], [4, 5], [4, 6], [5, 1], [5, 2], [5, 3], [5, 4], [6, 1], [6, 2], [6, 3], [6, 4],
    #      [7, 1], [7, 2], [7, 3], [7, 4], [7, 5], [8, 1], [8, 2], [8, 3], [8, 4], [9, 1], [9, 2], [9, 3], [9, 4], [10, 1],
    #      [10, 2], [10, 3], [10, 4], [11, 1], [11, 2], [11, 3], [11, 4], [11, 5], [11, 6], [11, 7], [12, 1], [12, 2], [12, 3],
    #      [12, 4], [13, 1], [13, 2], [13, 3], [13, 4], [13, 5], [14, 1], [14, 2], [14, 3], [14, 4], [14, 5], [15, 1], [15, 2],
    #      [15, 3], [15, 4], [15, 5], [16, 1], [16, 2], [16, 3], [16, 4], [16, 5], [17, 1], [17, 2], [17, 3], [17, 4], [18, 1],
    #      [18, 2], [18, 3], [18, 4], [19, 1], [19, 2], [19, 3], [19, 4], [20, 1], [20, 2], [20, 3], [20, 4], [21, 1], [21, 2],
    #      [21, 3], [21, 4], [21, 5], [22, 1], [22, 2], [22, 3], [22, 4], [22, 5], [22, 6], [23, 1], [23, 2], [23, 3], [23, 4],
    #      [24, 1], [24, 2], [24, 3], [24, 4], [25, 1], [25, 2], [25, 3], [25, 4], [25, 5], [26, 1], [26, 2], [26, 3], [26, 4],
    #      [27, 1], [27, 2], [27, 3], [27, 4], [27, 5], [28, 1], [28, 2], [28, 3], [28, 4], [29, 1], [29, 2], [29, 3], [29, 4],
    #      [30, 1], [30, 2], [30, 3], [30, 4], [31, 1], [31, 2], [31, 3], [31, 4], [32, 1], [32, 2], [32, 3], [32, 4], [32, 5],
    #      [32, 6], [33, 1], [33, 2], [33, 3], [33, 4], [34, 1], [34, 2], [34, 3], [34, 4], [35, 1], [35, 2], [35, 3], [35, 4],
    #      [36, 1], [36, 2], [36, 3], [36, 4], [37, 1], [37, 2], [37, 3], [37, 4], [37, 5], [38, 1], [38, 2], [38, 3], [38, 4],
    #      [39, 1], [39, 2], [39, 3], [39, 4], [40, 1], [40, 2], [40, 3], [40, 4], [41, 1], [41, 2], [41, 3], [41, 4], [42, 1],
    #      [42, 2], [42, 3], [42, 4], [43, 1], [43, 2], [43, 3], [43, 4], [44, 1], [44, 2], [44, 3], [44, 4], [44, 5], [45, 1],
    #      [45, 2], [45, 3], [45, 4], [45, 5], [46, 1], [46, 2], [46, 3], [46, 4], [46, 5], [47, 1], [47, 2], [47, 3], [47, 4],
    #      [47, 5], [48, 1], [48, 2], [48, 3], [48, 4], [49, 1], [49, 2], [49, 3], [49, 4], [50, 1], [50, 2], [50, 3], [50, 4],
    #      [51, 1], [51, 2], [51, 3], [51, 4], [51, 5], [51, 6], [52, 1], [52, 2], [52, 3], [52, 4], [53, 1], [53, 2], [53, 3],
    #      [53, 4], [53, 5], [54, 1], [54, 2], [54, 3], [54, 4], [54, 5], [55, 1], [55, 2], [55, 3], [55, 4], [56, 1], [56, 2],
    #      [56, 3], [56, 4], [57, 1], [57, 2], [57, 3], [57, 4], [58, 1], [58, 2], [58, 3], [58, 4], [59, 1], [59, 2], [59, 3],
    #      [59, 4], [59, 5], [59, 6], [59, 7], [60, 1], [60, 2], [60, 3], [60, 4], [61, 1], [61, 2], [61, 3], [61, 4], [62, 1],
    #      [62, 2], [62, 3], [62, 4], [63, 1], [63, 2], [63, 3], [63, 4], [64, 1], [64, 2], [64, 3], [64, 4], [64, 5], [65, 1],
    #      [65, 2], [65, 3], [65, 4], [66, 1], [66, 2], [66, 3], [66, 4], [66, 5]]

    # c ponizej dla pliku net12New2.txt
    c = [[1, 1, 1], [1, 2, 1], [1, 3, 1], [1, 4, 1], [2, 1, 1], [2, 2, 1], [2, 3, 1], [2, 4, 1], [3, 1, 1], [3, 2, 1], [3, 3, 1], [3, 4, 1], [3, 5, 1], [3, 6, 1], [4, 1, 1], [4, 2, 1], [4, 3, 1], [4, 4, 1], [4, 5, 1], [4, 6, 1], [5, 1, 1], [5, 2, 1], [5, 3, 1], [5, 4, 1], [6, 1, 1], [6, 2, 1], [6, 3, 1], [6, 4, 1], [7, 1, 1], [7, 2, 1], [7, 3, 1], [7, 4, 1], [7, 5, 1], [8, 1, 1], [8, 2, 1], [8, 3, 1], [8, 4, 1], [9, 1, 1], [9, 2, 1], [9, 3, 1], [9, 4, 1], [10, 1, 1], [10, 2, 1], [10, 3, 1], [10, 4, 1], [11, 1, 1], [11, 2, 1], [11, 3, 1], [11, 4, 1], [11, 5, 1], [11, 6, 1], [11, 7, 1], [12, 1, 1], [12, 2, 1], [12, 3, 1], [12, 4, 1], [13, 1, 1], [13, 2, 1], [13, 3, 1], [13, 4, 1], [13, 5, 1], [14, 1, 1], [14, 2, 1], [14, 3, 1], [14, 4, 1], [14, 5, 1], [15, 1, 1], [15, 2, 1], [15, 3, 1], [15, 4, 1], [15, 5, 1], [16, 1, 1], [16, 2, 1], [16, 3, 1], [16, 4, 1], [16, 5, 1], [17, 1, 1], [17, 2, 1], [17, 3, 1], [17, 4, 1], [18, 1, 1], [18, 2, 1], [18, 3, 1], [18, 4, 1], [19, 1, 1], [19, 2, 1], [19, 3, 1], [19, 4, 1], [20, 1, 1], [20, 2, 1], [20, 3, 1], [20, 4, 1], [21, 1, 1], [21, 2, 1], [21, 3, 1], [21, 4, 1], [21, 5, 1], [22, 1, 1], [22, 2, 1], [22, 3, 1], [22, 4, 1], [22, 5, 1], [22, 6, 1], [23, 1, 1], [23, 2, 1], [23, 3, 1], [23, 4, 1], [24, 1, 1], [24, 2, 1], [24, 3, 1], [24, 4, 1], [25, 1, 1], [25, 2, 1], [25, 3, 1], [25, 4, 1], [25, 5, 1], [26, 1, 1], [26, 2, 1], [26, 3, 1], [26, 4, 1], [27, 1, 1], [27, 2, 1], [27, 3, 1], [27, 4, 1], [27, 5, 1], [28, 1, 1], [28, 2, 1], [28, 3, 1], [28, 4, 1], [29, 1, 1], [29, 2, 1], [29, 3, 1], [29, 4, 1], [30, 1, 1], [30, 2, 1], [30, 3, 1], [30, 4, 1]]

    pathLimit = 3

    print("--- Binary Branch-and-Bound (with CPLEX) ---")
    best_solution, best_value = branch_and_bound_best_first(c)
    print("--- RES ---")
    print("Best Solution (Binary):", best_solution)
    print("Best Value (Binary):", best_value)

    for i in xrange(0, len(best_solution)):
        print(str(c[i][0]) + " " + str(c[i][1]) + " , val:" + str(best_solution[i]))
