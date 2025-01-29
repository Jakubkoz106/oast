import math
import pprint
import random
import copy


def load_input(file_path):
    with open(file_path, 'r') as file:
        data = [line.strip() for line in file if line.strip()]

    max_node_line = next(line for line in data if line.startswith("param maxNode"))
    module_capacity_line = next(line for line in data if line.startswith("param module_capacity"))
    max_node = int(max_node_line.split(":=")[1].strip(";"))
    module_capacity = int(module_capacity_line.split(":=")[1].strip(";"))

    links_start = data.index("param: Links: link_nodeA link_nodeZ number_of_modules:=") + 1
    links_end = next(i for i, line in enumerate(data[links_start:], start=links_start) if line.strip() == ";")
    links = []
    for line in data[links_start:links_end]:
        link_id, node_a, node_z, modules = map(int, line.split())
        links.append({'id': link_id, 'nodeA': node_a, 'nodeB': node_z, 'modules': modules})

    demands_start = data.index("param: Demands: demand_maxPath, demand_volume :=") + 1
    demands_end = next(i for i, line in enumerate(data[demands_start:], start=demands_start) if line.strip() == ";")
    demands = []
    for line in data[demands_start:demands_end]:
        demand_id, max_path, volume = map(int, line.split())
        demands.append({'id': demand_id, 'nodeA': None, 'nodeB': None, 'volume': volume, 'paths': []})

    for line in data[demands_end + 1:]:
        if line.startswith("set Demand_pathLinks["):
            demand_id, path_id = map(int, line.split("[")[1].split("]")[0].split(","))
            path_links = list(map(int, line.split(":=")[1].strip(" ;").split()))
            for demand in demands:
                if demand['id'] == demand_id:
                    while len(demand['paths']) < path_id:
                        demand['paths'].append([])
                    demand['paths'][path_id - 1] = path_links

    return module_capacity, links, demands


def fitness_functionDDAP(chromosome, demands, links, module_capacity):
    link_loads = {link['id']: 0 for link in links}
    for demand, allocation in zip(demands, chromosome):
        for path_idx, flow in enumerate(allocation):
            for link_id in demand['paths'][path_idx]:
                link_loads[link_id] += flow

    cost = 0
    for link in links:
        load = link_loads[link['id']]
        modules_required = math.ceil(load / module_capacity)
        cost += modules_required * link['cost']
    return cost


def fitness_functionDAP(chromosome, demands, links, moduleCapacity, bestRes=False):
    max_overload = float('-inf')
    link_loads = {link['id']: 0 for link in links}
    for demand, allocation in zip(demands, chromosome):
        for path_idx, flow in enumerate(allocation):
            for link_id in demand['paths'][path_idx]:
                link_loads[link_id] += flow

    for link in links:
        load = link_loads[link['id']]
        capacity = link['modules'] * 2
        overload = load - capacity
        if bestRes:
            print(overload)
        max_overload = max(max_overload, overload)

    if bestRes:
        print(link_loads)
        print(max_overload)
    return max_overload


def mutate_with_constraints(chromosome, demands, max_paths_with_flow, min_flow):
    demand_idx = random.randint(0, len(chromosome) - 1)
    allocation = chromosome[demand_idx]
    demand = demands[demand_idx]
    active_paths = [i for i, flow in enumerate(allocation) if flow > 0]

    if len(active_paths) < max_paths_with_flow and random.random() < 0.5:
        inactive_paths = [i for i in range(len(demand['paths'])) if i not in active_paths]
        if inactive_paths:
            new_path_idx = random.choice(inactive_paths)
            allocation[new_path_idx] += min_flow
    else:
        if active_paths:
            path_idx = random.choice(active_paths)
            if allocation[path_idx] > min_flow:
                allocation[path_idx] -= 1
                other_idx = random.choice(active_paths)
                allocation[other_idx] += 1


def crossover(parent1, parent2, demands, max_paths_with_flow, min_flow):

    point = random.randint(1, len(parent1) - 1)
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]

    child1 = repair_chromosome(child1, demands, max_paths_with_flow, min_flow)
    child2 = repair_chromosome(child2, demands, max_paths_with_flow, min_flow)
    return child1, child2


def repair_chromosome(chromosome, demands, max_paths_with_flow, min_flow):

    for demand_idx, allocation in enumerate(chromosome):
        demand = demands[demand_idx]
        active_paths = [i for i, flow in enumerate(allocation) if flow > 0]

        # dezaktywowanie losowej sciezki jesli path limit przekracza
        if len(active_paths) > max_paths_with_flow:
            excess_paths = random.sample(active_paths, len(active_paths) - max_paths_with_flow)
            for path_idx in excess_paths:
                allocation[path_idx] = 0

        # czy przeplywy spelniaja ograniczenie dolne
        active_paths = [i for i, flow in enumerate(allocation) if flow > 0]
        for path_idx in active_paths:
            if allocation[path_idx] < min_flow:
                allocation[path_idx] = min_flow

        # dodanie sumy przeplywow do wolumenu zapotrzebowania
        total_flow = sum(allocation)
        remaining_volume = demand['volume'] - total_flow

        # rozdziel pozostaly przeplyw miedzy aktywne sciezki
        while remaining_volume > 0:
            path_idx = random.choice(active_paths)
            allocation[path_idx] += 1
            remaining_volume -= 1

        while remaining_volume < 0:
            reducible_paths = [idx for idx in active_paths if allocation[idx] >= min_flow]
            if not reducible_paths:
                break

            path_idx = random.choice(reducible_paths)
            allocation[path_idx] -= 1
            remaining_volume += 1

    return chromosome



def initialize_population_with_constraints(pop_size, demands, max_paths_with_flow, min_flow):
    population = []
    for _ in range(pop_size):
        chromosome = []
        for demand in demands:
            allocation = [0] * len(demand['paths'])

            max_possible_paths = min(max_paths_with_flow, len(demand['paths']))
            num_paths_to_choose = random.randint(1, max_possible_paths)
            active_paths = random.sample(range(len(demand['paths'])), num_paths_to_choose)

            remaining_volume = demand['volume']
            for path_idx in active_paths:
                if min_flow < remaining_volume:
                    flow = random.randint(min_flow + 1, remaining_volume)
                else:
                    break
                allocation[path_idx] += flow
                remaining_volume -= flow
            while remaining_volume > 0:
                active_paths_with_flow = [idx for idx in active_paths if allocation[idx] > 0]
                path_idx = random.choice(active_paths_with_flow)
                allocation[path_idx] += 1
                remaining_volume -= 1
            chromosome.append(allocation)
        population.append(chromosome)
    return population


def select_new_parents_from_population(fitness_values, population, pop_size):
    sorted_fitness_population = sorted(zip(fitness_values, population))

    sorted_fitness_values, sorted_population = zip(*sorted_fitness_population)
    sorted_fitness_values = list(sorted_fitness_values)

    weighted_population = list(zip(sorted_fitness_population, sorted_fitness_values))

    selected_parents = []
    fitness_selected_parents = []
    for _ in range(pop_size):
        total_fitness = sum(weight for _, weight in weighted_population)
        probabilities = [weight / total_fitness for _, weight in weighted_population]
        probabilities.reverse()

        selected = random.choices([item[0] for item in weighted_population], weights=probabilities, k=1)[0]
        selected_parents.append(selected[1])
        fitness_selected_parents.append(selected[0])

        new_population = []
        found = False  # Flaga do pominiecia jednego elementu

        for chromosome, weight in weighted_population:
            if chromosome == selected and not found:
                found = True
                continue
            new_population.append((chromosome, weight))

        weighted_population = new_population

    return selected_parents, fitness_selected_parents


# Główna funkcja EA
def evolutionary_algorithm(file_path, generations=2000, pop_size=500, mutation_rate=0.2, k=200, dap=True):
    min_flow = 5
    max_paths = 2
    module_capacity, links, demands = load_input(file_path)
    population = initialize_population_with_constraints(pop_size, demands, max_paths, min_flow)

    # Ocena populacji
    if dap:
        fitness_values = [fitness_functionDAP(chromo, demands, links, module_capacity) for chromo in population]
    else:
        fitness_values = [fitness_functionDDAP(chromo, demands, links, module_capacity) for chromo in population]

    # Aktualizacja najlepszego rozwiązania
    best_cost = min(fitness_values)
    best_solution = population[fitness_values.index(best_cost)]

    for gen in range(generations):
        sorted_population = [x for _, x in sorted(zip(fitness_values, population))]

        offspring = []
        for i in range(k):
            p1, p2 = random.sample(population, 2)
            c1, c2 = crossover(p1, p2,demands,max_paths,min_flow)
            offspring.append(c1)
            offspring.append(c2)

        for child in offspring:
            if random.random() < mutation_rate:
                mutate_with_constraints(child, demands, max_paths, min_flow)

        population = sorted_population + offspring

        # Ocena populacji
        if dap:
            fitness_values = [fitness_functionDAP(chromo, demands, links, module_capacity) for chromo in population]
        else:
            fitness_values = [fitness_functionDDAP(chromo, demands, links, module_capacity) for chromo in population]

        # Aktualizacja najlepszego rozwiązania
        current_best_cost = min(fitness_values)
        current_best_solution = population[fitness_values.index(current_best_cost)]

        if current_best_cost < best_cost:
            best_cost = current_best_cost
            best_solution = copy.deepcopy(current_best_solution)
            print(best_cost)
            print(best_solution)


        pprint.pprint(current_best_cost)
        if current_best_cost <= 0 :
            return best_solution, best_cost
        population, fitness_values = select_new_parents_from_population(fitness_values, population, pop_size)

        population[0] = best_solution
        fitness_values[0] = best_cost

        print(f"Generacja {gen + 1}: Najlepszy koszt/z = {best_cost}")

    if dap: fitness_functionDAP(best_solution, demands, links, module_capacity, True)
    return best_solution, best_cost


# Uruchomienie algorytmu
best_solution, best_cost = evolutionary_algorithm("net12New.txt")
print("Najlepsze rozwiązanie:", best_solution)
print("Najniższy koszt/z:", best_cost)
