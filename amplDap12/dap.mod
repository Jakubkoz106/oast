param maxNode, >= 0, integer;
param module_capacity, >= 0;  # Pojemność jednego modułu

set Nodes = 1..maxNode;

set Links;
param link_nodeA {Links}, in Nodes;
param link_nodeZ {Links}, in Nodes;
param number_of_modules {Links}, >= 0;
#param module_cost {Links}, >= 0;


set Demands;
param demand_maxPath {Demands}, >= 0;
param demand_volume {Demands}, >= 0;
set Demand_pathLinks {demand in Demands, demandPath in 1..demand_maxPath[demand]} within Links;


var pathDemand_volumeCount {demand in Demands, 1..demand_maxPath[demand]}, >= 0; #, integer
var linkDemand_volumeCount {Links}, >= 0;
var z, >= 0;  


# Ograniczenia

# Zaspokojenie wolumenu żądania
subject to satisfying_demand_volume {demand in Demands}:
    sum {demandPath in 1..demand_maxPath[demand]} pathDemand_volumeCount[demand, demandPath] = demand_volume[demand];

# Liczba volume na linku wynikająca z obciążenia
subject to linkDemand_volumeCount_constraint {link in Links}:
    linkDemand_volumeCount[link] = 
    sum {demand in Demands, demandPath in 1..demand_maxPath[demand]: link in Demand_pathLinks[demand, demandPath]}
    	pathDemand_volumeCount[demand, demandPath];

# Limit modułów na łączu
subject to link_modules_constraint {link in Links}:
    linkDemand_volumeCount[link] <= number_of_modules[link] * module_capacity + z;

# Funkcja celu - minimalizacja maksymalnej wartości `z`
minimize TotalModules: z;


# Problem DAP
problem dap:
    TotalModules,
    pathDemand_volumeCount, linkDemand_volumeCount, z,
    satisfying_demand_volume, linkDemand_volumeCount_constraint, link_modules_constraint;
