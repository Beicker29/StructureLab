from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from deap import base, creator, tools

CandidateT = TypeVar("CandidateT")
Genome = list[int]


@dataclass(frozen=True)
class SearchHooks(Generic[CandidateT]):
    evaluate: Callable[[Genome], CandidateT]
    score: Callable[[CandidateT], float]
    objective: Callable[[CandidateT], float]
    is_feasible: Callable[[CandidateT], bool]
    failure_mode: Callable[[CandidateT], str]
    tie_break: Callable[[CandidateT], Any] | None = None


def _has_better_objective(
    candidate: CandidateT,
    current: CandidateT,
    hooks: SearchHooks[CandidateT],
) -> bool:
    candidate_objective = hooks.objective(candidate)
    current_objective = hooks.objective(current)
    if candidate_objective < current_objective:
        return True
    if candidate_objective != current_objective or hooks.tie_break is None:
        return False
    return hooks.tie_break(candidate) < hooks.tie_break(current)


@dataclass(frozen=True)
class SearchOutcome(Generic[CandidateT]):
    selected: CandidateT
    evaluated_candidates: int
    feasible_candidates: int
    failure_counts: dict[str, int]


def run_exhaustive_search(
    *,
    domain_sizes: list[int],
    hooks: SearchHooks[CandidateT],
) -> SearchOutcome[CandidateT]:
    evaluated = 0
    feasible = 0
    failure_counts: dict[str, int] = {}
    best_seen: CandidateT | None = None
    best_feasible: CandidateT | None = None

    for genes in itertools.product(*(range(size) for size in domain_sizes)):
        individual = [int(gene) for gene in genes]
        candidate = hooks.evaluate(individual)
        evaluated += 1
        failure_key = hooks.failure_mode(candidate)
        failure_counts[failure_key] = failure_counts.get(failure_key, 0) + 1

        if hooks.is_feasible(candidate):
            feasible += 1
            if best_feasible is None or _has_better_objective(candidate, best_feasible, hooks):
                best_feasible = candidate

        if best_seen is None or hooks.score(candidate) < hooks.score(best_seen):
            best_seen = candidate

    selected = best_feasible if best_feasible is not None else best_seen
    if selected is None:
        raise RuntimeError("No candidate was evaluated in exhaustive mode")

    return SearchOutcome(
        selected=selected,
        evaluated_candidates=evaluated,
        feasible_candidates=feasible,
        failure_counts=failure_counts,
    )


def run_genetic_search(
    *,
    domain_sizes: list[int],
    population_size: int,
    generations: int,
    crossover_rate: float,
    mutation_rate: float,
    elite_count: int,
    hooks: SearchHooks[CandidateT],
    seed: int,
    fitness_class_name: str,
    individual_class_name: str,
) -> SearchOutcome[CandidateT]:
    rng = random.Random(seed)
    _ensure_deap_types(
        fitness_class_name=fitness_class_name,
        individual_class_name=individual_class_name,
    )

    toolbox = base.Toolbox()
    individual_cls = getattr(creator, individual_class_name)
    candidates_by_genome: dict[tuple[int, ...], CandidateT] = {}

    def create_individual() -> Genome:
        return [rng.randrange(size) for size in domain_sizes]

    def clone_individual(individual: Genome) -> Genome:
        return individual_cls(individual)

    def mate(ind_a: Genome, ind_b: Genome) -> tuple[Genome, Genome]:
        for index in range(len(ind_a)):
            if rng.random() < 0.5:
                ind_a[index], ind_b[index] = ind_b[index], ind_a[index]
        return ind_a, ind_b

    def mutate(individual: Genome) -> tuple[Genome]:
        for index, size in enumerate(domain_sizes):
            if rng.random() < mutation_rate:
                individual[index] = rng.randrange(size)
        return (individual,)

    def tournament_pick(population: list[Genome], k: int = 3) -> Genome:
        pool = [rng.choice(population) for _ in range(k)]
        return min(pool, key=individual_rank)

    def individual_rank(individual: Genome) -> tuple[Any, ...]:
        fitness = individual.fitness.values[0]
        if hooks.tie_break is None:
            return (fitness,)
        candidate = candidates_by_genome[tuple(int(gene) for gene in individual)]
        return fitness, hooks.tie_break(candidate)

    toolbox.register("individual", tools.initIterate, individual_cls, create_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("clone", clone_individual)
    toolbox.register("mate", mate)
    toolbox.register("mutate", mutate)

    population = toolbox.population(n=population_size)
    evaluated = 0
    feasible = 0
    failure_counts: dict[str, int] = {}
    best_seen: CandidateT | None = None
    best_feasible: CandidateT | None = None

    for _ in range(generations):
        for individual in population:
            candidate = hooks.evaluate(individual)
            candidates_by_genome[tuple(int(gene) for gene in individual)] = candidate
            evaluated += 1
            individual.fitness.values = (hooks.score(candidate),)
            failure_key = hooks.failure_mode(candidate)
            failure_counts[failure_key] = failure_counts.get(failure_key, 0) + 1

            if hooks.is_feasible(candidate):
                feasible += 1
                if best_feasible is None or _has_better_objective(candidate, best_feasible, hooks):
                    best_feasible = candidate

            if best_seen is None or hooks.score(candidate) < hooks.score(best_seen):
                best_seen = candidate

        elites = [
            toolbox.clone(individual)
            for individual in sorted(population, key=individual_rank)[:elite_count]
        ]
        next_population = elites
        while len(next_population) < population_size:
            parent_a = toolbox.clone(tournament_pick(population))
            parent_b = toolbox.clone(tournament_pick(population))
            if rng.random() < crossover_rate:
                parent_a, parent_b = toolbox.mate(parent_a, parent_b)
            parent_a, = toolbox.mutate(parent_a)
            parent_b, = toolbox.mutate(parent_b)
            if hasattr(parent_a.fitness, "values"):
                del parent_a.fitness.values
            if hasattr(parent_b.fitness, "values"):
                del parent_b.fitness.values
            next_population.append(parent_a)
            if len(next_population) < population_size:
                next_population.append(parent_b)
        population = next_population

    selected = best_feasible if best_feasible is not None else best_seen
    if selected is None:
        raise RuntimeError("GA produced no candidates")

    return SearchOutcome(
        selected=selected,
        evaluated_candidates=evaluated,
        feasible_candidates=feasible,
        failure_counts=failure_counts,
    )


def _ensure_deap_types(*, fitness_class_name: str, individual_class_name: str) -> None:
    if not hasattr(creator, fitness_class_name):
        creator.create(fitness_class_name, base.Fitness, weights=(-1.0,))
    if not hasattr(creator, individual_class_name):
        fitness_cls = getattr(creator, fitness_class_name)
        creator.create(individual_class_name, list, fitness=fitness_cls)
