"""Class allowing for better multiple training runs."""
from pgn.load_data import process_raw
from pgn.data.load_data import load_proximity_graphs
from pgn.train.train_model import train_model
from pgn.train.train_utils import load_checkpoint
from pgn.train.cross_validate_model import cross_validation

class Trainer():
    """Class that loaders and holds the arguments and data objects. Allows for easy evaluation and retraining when the
    same data is going to be used multiple times."""
    def __init__(self, args):
        #Need to see if this is going to work with subparsers
        self.args = args
        self.load_data()
        self.model = None

    def load_data(self):
        #TODO: Fix weird issue that tries to remake folders
        if self.args.construct_graphs:
            process_raw(self.args)
        if self.args.cross_validate:
            if self.args.load_test:
                self.train_data, self.test_data = load_proximity_graphs(self.args)
            else:
                self.train_data = load_proximity_graphs(self.args)
        if self.args.load_test:
            self.train_data, self.valid_data, self.test_data = load_proximity_graphs(self.args)
        else:
            self.train_data, self.valid_data = load_proximity_graphs(self.args)

    def set_hyperopt_args(self, hyperopt_args, reload_data=False):
        """
        Changes the arguments used for training. The data arguments must be the same as initialization args unless
        load_data is set to true
        :param hyperopt_args: The new argument object.
        :param reload_data: Bool toggle to determine whether the data will be reloaded.
        :return: None
        """
        self.args = hyperopt_args
        if reload_data:
            self.load_data()

    def run_training(self):
        """
        Runs training.
        :return:
        """
        if self.args.cross_validate:
            self.model, self.valid_eval = cross_validation(self.args, self.train_data)
        else:
            self.model, self.valid_eval = train_model(self.args, self.train_data, self.valid_data)

    def get_score(self):
        """
        Returns the score
        :return:
        """
        if self.model is None:
            raise RuntimeError("Score attempted to be retrieved before model trained.")
        return self.valid_eval[self.args.loss_function]

    def load_checkpoint(self, path):
        """
        Loads a checkpoint file and sets it to the model to be used in training.
        :param path: The path of the checkpoint file to be loaded.
        """
        self.model, self.args = load_checkpoint(path,
                                      device=self.args.device,
                                      return_args=True)
