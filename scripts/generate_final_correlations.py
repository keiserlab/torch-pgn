import sys
import os
sys.path.insert(0, "/srv/home/zgaleday/torch_pgn")

from torch_pgn.train.Trainer import Trainer
from torch_pgn.train.train_utils import load_args
from torch_pgn.train.run_training import run_training

import numpy as np
import pandas as pd

import os.path as osp
import os


def generate_final_correlations(checkpoint_path, final_path, split_path, device, repeats=5, epochs=300, data_path=None, control=None):
    """
    Loads the checkpoint. Gives a random seed and generates <repeats> models with the same hyperparamters and different initialization.
    :param checkpoint_path: The path of the checkpoint file to load the args from.
    :param final_path: The path to save the results into.
    :param split_path: The path where the splits used to train the model were saved. Only the testing split is used (to ensure no data contamination).
    :param device: device to use for training
    :param repeats: The number of trails to run.
    :return: None
    """
    val_evals = []
    label_stats = []
    args = load_args(checkpoint_path, device=device)
    args.construct_graphs = False
    args.split_type = 'defined_test'
    args.split_dir = split_path
    args.mode = 'evaluate'
    args.load_test = True
    args.num_workers = 0
    args.epochs = epochs
    args.cross_validate = False
    print(args)
    if control is not None:
        if control == 'ligand':
            args.ligand_only = True
        elif control == 'PE':
            args.interaction_edges_removed = True
        elif control == 'straw':
            args.straw_model = True
        elif control == 'ligand_readout':
            args.ligand_only_readout = True
        elif control == 'split_conv':
            args.split_conv = True
        elif control == 'two_step_mpnn':
            args.covalent_only_depth = 2
            args.depth = 5
        elif control == 'two_step_split':
            args.split_conv = True
            args.covalent_only_depth = 2
            args.depth = 5
        elif control == 'two_step_split_ligand':
            args.ligand_only_readout = True
            args.split_conv = True
            args.covalent_only_depth = 2
            args.depth = 5
        elif control == 'no_dist':
            args.include_dist = False
    if data_path is not None:
        args.data_path = data_path
    base_dir = final_path

    for iter in range(repeats):

        save_dir = osp.join(base_dir, 'repeat_{0}'.format(iter))
        os.mkdir(save_dir)
        args.save_dir = save_dir
        args.seed = np.random.randint(0, 1e4)
        trainer = run_training(args)
        val_evals.append(trainer.valid_eval)
        label_stats.append((float(args.label_mean), float(args.label_std)))
        # Cleanup
        trainer = None
        del trainer
    df = _format_evals(val_evals, label_stats)
    df.to_csv(osp.join(base_dir, 'eval_stats.csv'))


def _format_evals(val_evals, label_stats):
    evals = {}
    for key in val_evals[0].keys():
        evals['test_' + key] = []
    evals['mean'] = []
    evals['std'] = []
    for idx in range(len(val_evals)):
        evals['mean'].append(label_stats[idx][0])
        evals['std'].append(label_stats[idx][1])
        for key in val_evals[idx].keys():
            evals['test_' + key].append(val_evals[idx][key])
    return pd.DataFrame(evals)

if __name__ == '__main__':
    checkpoint_path = sys.argv[1]
    final_path = sys.argv[2]
    split_path = sys.argv[3]
    device = sys.argv[4]
    epochs = int(sys.argv[5])
    data_path = None
    control = None
    if len(sys.argv) > 6:
        data_path = sys.argv[6]
        control = sys.argv[7]
    generate_final_correlations(checkpoint_path, final_path, split_path, device, epochs=epochs, data_path=data_path, control=control, repeats=3)
