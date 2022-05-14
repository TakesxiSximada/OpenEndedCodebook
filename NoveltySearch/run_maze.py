import sys
import os
import shutil
import json
import numpy as np


import ns_neat
from parallel import ParallelEvaluator

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
UTIL_DIR = os.path.join(CURR_DIR, 'maze_utils')
sys.path.append(UTIL_DIR)
from arguments import get_args
from drawer import DrawReporter

from maze_environment_numpy import MazeEnvironment


class MazeEvaluator():
    def __init__(self, maze, timesteps):
        self.maze = maze
        self.timesteps = timesteps

    def evaluate_agent(self, key, controller, generation):
        self.maze.reset()

        done = False
        for i in range(self.timesteps):
            obs = self.maze.get_observation()
            action = controller.activate(obs)
            done = self.maze.update(action)
            if done:
                break

        if done:
            reward = 1.0
        else:
            distance = self.maze.get_distance_to_exit()
            reward = (self.maze.initial_distance - distance) / self.maze.initial_distance

        last_loc = self.maze.get_agent_location()
        results = {
            'reward': reward,
            'data': [last_loc[0], last_loc[1]]
        }
        return results


def main():
    args = get_args()

    save_path = os.path.join(CURR_DIR, 'maze_out', args.name)

    try:
        os.makedirs(save_path)
    except:
        print(f'THIS EXPERIMENT ({args.name}) ALREADY EXISTS')
        print('Override? (y/n): ', end='')
        ans = input()
        if ans.lower() == 'y':
            shutil.rmtree(save_path)
            os.makedirs(save_path)
        else:
            return
        print()

    argument_file = os.path.join(save_path, 'arguments.json')
    with open(argument_file, 'w') as f:
        json.dump(args.__dict__, f, indent=4)


    maze_env_config = os.path.join(UTIL_DIR, f'{args.task}_maze.txt')
    maze_env = MazeEnvironment.read_environment(maze_env_config)


    evaluator = MazeEvaluator(maze_env, args.timesteps)
    parallel = ParallelEvaluator(
        num_workers=args.num_cores,
        evaluate_function=evaluator.evaluate_agent,
        decode_function=ns_neat.FeedForwardNetwork.create
    )

    config_path = os.path.join(UTIL_DIR, 'ns_config.ini')
    overwrite_config = [
        ('NS-NEAT', 'pop_size', args.pop_size),
        ('NS-NEAT', 'metric', 'manhattan'),
        ('NS-NEAT', 'threshold_init', args.ns_threshold),
        ('NS-NEAT', 'threshold_floor', 0.25),
        ('NS-NEAT', 'neighbors', args.num_knn),
        ('NS-NEAT', 'mcns', args.mcns),
    ]
    config = ns_neat.make_config(config_path, custom_config=overwrite_config)
    config_out_path = os.path.join(save_path, 'ns_config.ini')
    config.save(config_out_path)


    pop = ns_neat.Population(config)

    figure_path = os.path.join(save_path, 'progress')
    reporters = [
        ns_neat.SaveResultReporter(save_path),
        ns_neat.NoveltySearchReporter(True),
        DrawReporter(maze_env, args.timesteps, figure_path, no_plot=args.no_plot)
    ]
    for reporter in reporters:
        pop.add_reporter(reporter)


    pop.run(evaluate_function=parallel.evaluate, n=args.generation)

if __name__=='__main__':
    main()
