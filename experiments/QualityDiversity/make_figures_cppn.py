import os
import sys
import csv

import multiprocessing as mp


import evogym.envs

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURR_DIR))

LIB_DIR = os.path.join(ROOT_DIR, 'libs')
sys.path.append(LIB_DIR)
from experiment_utils import load_experiment

ENV_DIR = os.path.join(ROOT_DIR, 'envs', 'evogym')
sys.path.append(ENV_DIR)
from figure_drawer import EvogymStructureDrawerCPPN, pool_init_func


from arguments.evogym_me_cppn import get_figure_args


def main():

    args = get_figure_args()

    expt_path = os.path.join(CURR_DIR, 'out', 'evogym_me_cppn', args.name)
    expt_args = load_experiment(expt_path)


    robot_ids = {}
    if args.specified is not None:
        robot_ids = {
            'specified': [args.specified]
        }
    else:
        files = {
            'population': 'history_pop.csv',
        }
        for metric,file in files.items():

            history_file = os.path.join(expt_path, file)
            with open(history_file, 'r') as f:
                reader = csv.reader(f)
                histories = list(reader)[1:]
                ids = sorted(list(set([hist[1] for hist in histories])))
                robot_ids[metric] = ids


    figure_path = os.path.join(expt_path, 'figure')
    draw_kwargs = {}
    if args.save_type=='gif':
        draw_kwargs = {
            'resolution': (1280*args.resolution_ratio, 720*args.resolution_ratio),
            'deterministic': args.deterministic
        }
    elif args.save_type=='jpg':
        draw_kwargs = {
            'interval': args.interval,
            'resolution_scale': args.resolution_scale,
            'timestep_interval': args.timestep_interval,
            'distance_interval': args.distance_interval,
            'display_timestep': args.display_timestep,
            'deterministic': args.deterministic
        }
    drawer = EvogymStructureDrawerCPPN(
        save_path=figure_path,
        env_id=expt_args['task'],
        overwrite=not args.not_overwrite,
        save_type=args.save_type, **draw_kwargs)

    draw_function = drawer.draw


    if not args.no_multi and args.specified is None:

        lock = mp.Lock()
        pool = mp.Pool(args.num_cores, initializer=pool_init_func, initargs=(lock,))
        jobs = []

        for metric,ids in robot_ids.items():
            for key in ids:
                structure_file = os.path.join(expt_path, 'structure', f'{key}.npz')
                ppo_file = os.path.join(expt_path, 'controller', f'{key}.zip')
                jobs.append(pool.apply_async(draw_function, args=(key, structure_file, ppo_file), kwds={'directory': metric}))

        for job in jobs:
            job.get(timeout=None)


    else:

        lock = mp.Lock()
        lock = pool_init_func(lock)

        for metric,ids in robot_ids.items():
            for key in ids:
                structure_file = os.path.join(expt_path, 'structure', f'{key}.npz')
                ppo_file = os.path.join(expt_path, 'controller', f'{key}.zip')
                draw_function(key, structure_file, ppo_file, directory=metric)

if __name__=='__main__':
    main()
