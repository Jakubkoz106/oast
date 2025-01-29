import math
import pprint
import random
import copy


def load_input(file_path):
    with open(file_path, 'r') as file:
        data = [line.strip() for line in file if line.strip()]

    # Wczytaj `maxNode` i `module_capacity`
    max_node_line = next(line for line in data if line.startswith("param maxNode"))
    module_capacity_line = next(line for line in data if line.startswith("param module_capacity"))
    max_node = int(max_node_line.split(":=")[1].strip(";"))
    module_capacity = int(module_capacity_line.split(":=")[1].strip(";"))

    # Wczytaj `Links`
    links_start = data.index("param: Links: link_nodeA link_nodeZ number_of_modules:=") + 1
    links_end = next(i for i, line in enumerate(data[links_start:], start=links_start) if line.strip() == ";")
    links = []
    for line in data[links_start:links_end]:
        link_id, node_a, node_z, modules = map(int, line.split())
        links.append({'id': link_id, 'nodeA': node_a, 'nodeB': node_z, 'modules': modules})

    # Wczytaj `Demands`
    demands_start = data.index("param: Demands: demand_maxPath, demand_volume :=") + 1
    demands_end = next(i for i, line in enumerate(data[demands_start:], start=demands_start) if line.strip() == ";")
    demands = []
    for line in data[demands_start:demands_end]:
        demand_id, max_path, volume = map(int, line.split())
        demands.append({'id': demand_id, 'nodeA': None, 'nodeB': None, 'volume': volume, 'paths': []})

    # Wczytaj `Demand_pathLinks`
    for line in data[demands_end + 1:]:
        if line.startswith("set Demand_pathLinks["):
            demand_id, path_id = map(int, line.split("[")[1].split("]")[0].split(","))
            path_links = list(map(int, line.split(":=")[1].strip(" ;").split()))
            # Dopisz ścieżki do odpowiedniego `demand`
            for demand in demands:
                if demand['id'] == demand_id:
                    while len(demand['paths']) < path_id:
                        demand['paths'].append([])  # Dodaj miejsce na ścieżki
                    demand['paths'][path_id - 1] = path_links

    return module_capacity, links, demands


# Funkcja fitness ddap
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


# Funkcja fitness dap
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


# Mutacja
def mutate(chromosome, demands):
    demand_idx = random.randint(0, len(chromosome) - 1)
    allocation = chromosome[demand_idx]
    demand = demands[demand_idx]
    path_idx = random.randint(0, len(demand['paths']) - 1)

    if allocation[path_idx] > 0:
        other_idx = random.choice([i for i in range(len(demand['paths'])) if i != path_idx])
        allocation[path_idx] -= 1
        allocation[other_idx] += 1


# Krzyżowanie
def crossover(parent1, parent2):
    point = random.randint(1, len(parent1) - 1)
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]
    return child1, child2


# Inicjalizacja populacji
def initialize_population(pop_size, demands):
    population = []
    for _ in range(pop_size):
        chromosome = []
        for demand in demands:
            allocation = [0] * len(demand['paths'])
            remaining_volume = demand['volume']
            while remaining_volume > 0:
                idx = random.randint(0, len(allocation) - 1)
                allocation[idx] += 1
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
def evolutionary_algorithm(file_path, generations=10000, pop_size=500, mutation_rate=0.1, k=300, dap=True):
    # tworzenie populacji
    module_capacity, links, demands = load_input(file_path)
    population = initialize_population(pop_size, demands)

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

        # Selekcja rodziców
        # parents, fitness_values = select_new_parents_from_population(fitness_values,population)  # sorted_population[:pop_size // 2]
        # parents = [x for _, x in sorted(zip(fitness_values, population))][:len(population)//2]
        # fitness_values = fitness_values[:len(fitness_values)//2]

        # Krzyżowanie
        offspring = []
        for i in range(k):
            p1, p2 = random.sample(population, 2)
            c1, c2 = crossover(p1, p2)
            offspring.append(c1)
            offspring.append(c2)

        # Mutacja
        for child in offspring:
            if random.random() < mutation_rate:
                mutate(child, demands)

        # Aktualizacja populacji z elityzmem
        # population = sorted_population[:pop_size // 4] + offspring[:3 * pop_size // 4]
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

        # wybierane są najlepsze N osobniki albo 239 + 240, albo 241

        # population = [x for _, x in sorted(zip(fitness_values, population))][:len(population)//2]
        # fitness_values = fitness_values[:len(fitness_values)//2]
        pprint.pprint(current_best_cost)
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
