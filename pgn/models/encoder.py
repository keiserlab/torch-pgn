import torch
import torch.nn.functional as F
from torch.nn import ReLU, Sequential, Linear, BatchNorm1d

from torch_geometric.nn import NNConv

from pgn.args import EncoderArgs
from pgn.models.nn_utils import get_sparse_fnctn, get_pool_function

class PFPEncoder(torch.nn.Module):
    """Message passing network used to encode interaction graphs for use in either regression or classification
    tasks."""
    def __init__(self, args: EncoderArgs, node_dim: int, bond_dim: int):
        super(PFPEncoder, self).__init__()
        self.node_dim = node_dim
        self.bond_dim = bond_dim
        self.device = args.device
        self.nn_conv_in_dim = args.nn_conv_in_dim
        self.nn_conv_internal_dim = args.nn_conv_internal_dim
        self.nn_conv_out_dim = args.nn_conv_out_dim
        self.nn_conv_aggr = args.nn_conv_aggr
        self.pool_type = args.pool_type
        self.sparse_type = args.sparse_type
        self.fp_norm = args.fp_norm
        self.fp_dim = args.fp_dim
        self.depth = args.depth
        self.skip_connections = args.skip_connections

        # define model layers
        self.construct_nn_conv()
        self.atom_expand_nn = Sequential(Linear(self.node_dim, self.nn_conv_in_dim), ReLU())
        self.pool = get_pool_function(self.pool_type)
        self.sparsify = get_sparse_fnctn(self.sparse_function, self.fp_dim)
        self.expand_to_fp_nn = Sequential(Linear(self.nn_conv_out_dim, self.fp_dim), ReLU())

        # define batch normalization
        if self.fp_norm:
            self.norm_layer = BatchNorm1d(num_features=self.fp_dim)

    def construct_nn_conv(self):
        #Construct the NN Conv network
        feed_forward = Sequential(Linear(self.node_dim, self.nn_conf_internal_dim),
                                  ReLU(),
                                  Linear(self.nn_conf_internal_dim, self.nn_conf_out_dim))
        self.conv = NNConv(self.nn_conv_in_dim, self.nn_conv_in_dim, feed_forward, aggr=self.nn_conv_aggr)


    def forward(self, data):
        # Define output vector
        fingerprint = torch.zeros(self.fp_dim, dtype=torch.float32, requires_grad=True, device=self.device)
        # Expand atom featurization for input to NNConv
        message = self.expand_atom_nn(data.x)
        # Begin message passing steps
        for i in range(self.depth):
            message = F.relu(self.conv(message, data.edge_index, data.edge_attr))
            # expand message for incorporation into final feature vector
            expanded_message = self.expand_to_fp_nn(message.unsqueeze(0))
            # readout for depth i
            readout = self.sparsify(self.pool(expanded_message.squeeze(0), data.batch))
            # skip connections if specified or final message passing step to readout vector
            if self.skip_connections or i == self.depth - 1:
                fingerprint = fingerprint + readout
        fingerprint = fingerprint.squeeze()
        if self.fp_norm:
            return self.fp_norm(fingerprint)
        else:
            return fingerprint

