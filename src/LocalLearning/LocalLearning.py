from abc import ABC, abstractmethod

import math
from pathlib import Path
from tqdm.autonotebook import tqdm

import copy

import torch
from torch.utils.data import DataLoader
from torch import nn
from torch import Tensor
from torch.optim import Adam


class KHL3(nn.Module):
    """
    Krotov and Hopfield's (KH) Local Learning Layer (L3)
    as first implemented by Konstantin Holzhausen
    CAREFUL - definition of g does not matches any of the ones mentioned in the paper
    """

    pSet = {
        "in_size": 28 ** 2,
        "hidden_size": 2000,
        "n": 4.5,
        "p": 3,
        "tau_l": 1 / 0.04,
        "k": 7,
        "Delta": 0.4,
        "R": 1.0,
    }

    def __init__(self, params: dict, sigma=None):
        super().__init__()

        self.pSet["in_size"] = params["in_size"]
        self.pSet["hidden_size"] = params["hidden_size"]
        self.pSet["n"] = params["n"]  # not used in this class, but belongs to the model
        self.pSet["p"] = params["p"]
        self.pSet["tau_l"] = params["tau_l"]
        self.pSet["k"] = params["k"]
        self.pSet["Delta"] = params["Delta"]
        self.pSet["R"] = params["R"]

        self.flatten = nn.Flatten()
        self.flatten.requires_grad_(False)
        #  initialize weights
        self.W = nn.Parameter(
            torch.zeros((self.pSet["in_size"], self.pSet["hidden_size"])),
            requires_grad=False,
        )
        # self.W = nn.Parameter(self.W) # W is a model parameter
        if type(sigma) == type(None):
            # if sigma is not explicitely specified, use Glorot
            # initialisation scheme
            sigma = 1.0 / math.sqrt(self.pSet["in_size"] + self.pSet["hidden_size"])
            
        self.W.normal_(mean=0.0, std=sigma)

    def __metric_tensor(self):
        eta = torch.abs(self.W)
        return torch.pow(eta, self.pSet["p"] - 2.0)

    def _bracket(self, v: Tensor, M: Tensor) -> Tensor:
        res = torch.mul(M, self.__metric_tensor())
        return torch.matmul(v, res)

    def __matrix_bracket(self, M_1: Tensor, M_2: Tensor) -> Tensor:
        res = torch.mul(M_1, self.__metric_tensor())
        res = torch.mul(M_2, res)
        return torch.sum(res, dim=0)

    def __g(self, q: Tensor) -> Tensor:
        g_q = torch.zeros(q.size(), device=self.W.device)
        _, sorted_idxs = q.topk(self.pSet["k"], dim=-1)
        batch_size = g_q.size(dim=0)
        g_q[range(batch_size), sorted_idxs[:, 0]] = 1.0
        g_q[range(batch_size), sorted_idxs[:, 1:]] = -self.pSet["Delta"]
        return g_q

    def __weight_increment(self, v: Tensor) -> Tensor:
        h = self._bracket(v, self.W)
        Q = torch.pow(
            self.__matrix_bracket(self.W, self.W),
            (self.pSet["p"] - 1.0) / self.pSet["p"],
        )
        Q = torch.div(h, Q)
        inc = (self.pSet["R"] ** self.pSet["p"]) * v[..., None] - torch.mul(
            h[:, None, ...], self.W
        )
        return torch.mul(self.__g(Q)[:, None, ...], inc).sum(dim=0)

    def forward(self, x):
        x_flat = self.flatten(x)
        return self._bracket(x_flat, self.W)

    def param_dict(self) -> dict:
        return self.pSet

    def eval(self) -> None:
        pass

    def train(self, mode: bool = True) -> None:
        pass

    def train_step(self, x: Tensor) -> None:
        # mean training, treating each mini batch as a sample:
        # dW = self.__weight_increment(x) / self.params.tau_l
        # dW_mean = torch.sum(dW, dim=0) / dW.size(dim=0)
        # self.W += dW_mean

        # sequential training in mini batch time:
        x_flat = self.flatten(x)
        for v in x_flat:
            v = v[None, ...]  # single element -> minibatch of size 1
            self.W += self.__weight_increment(v) / self.pSet["tau_l"]


class FKHL3(KHL3):
    """
    Fast AI implementation (F) of KHL3
    """

    def __init__(self, params: dict, sigma=None):
        super().__init__(params, sigma)

    # redefining the relevant routines to make them fast
    # "fast" means that it allows for parallel mini-batch processing

    def __g(self, q: Tensor) -> Tensor:
        g_q = torch.zeros(q.size(), device=self.W.device)
        _, sorted_idxs = q.topk(self.pSet["k"], dim=-1)
        batch_size = g_q.size(dim=0)
        g_q[range(batch_size), sorted_idxs[:, 0]] = 1.0
        g_q[range(batch_size), sorted_idxs[:, -1]] = -self.pSet["Delta"]
        return g_q

    def __weight_increment(self, v: Tensor) -> Tensor:
        h = self._bracket(v, self.W)
        g_mu = self.__g(h)
        inc = self.pSet["R"] ** self.pSet["p"] * (v.T @ g_mu)
        return inc - (g_mu * h).sum(dim=0)[None, ...] * self.W

    def train_step(self, x: Tensor, prec=1e-9) -> None:
        # implementation of the fast unsupervised
        # training algorithm
        # it is fast because it does not require sequential training over
        # minibatch

        x_flat = self.flatten(x)
        dW = self.__weight_increment(x_flat)
        nc = max(dW.abs().max(), prec)
        self.W += dW / (nc * self.pSet["tau_l"])


class HiddenLayerModel(nn.Module, ABC):
    
    pSet = {
        "hidden_size": 2000,
    }
    
    def __init__(self):
        super().__init__()
        setattr(self, 'forward', self._forward)
        self.device = torch.device('cpu')

    @abstractmethod
    def hidden(self, x: torch.Tensor):
        pass

    @abstractmethod
    def _forward(self, x: torch.Tensor):
        pass

    def pred(self):
        def preds(x: torch.Tensor) -> torch.Tensor:
            logits, hidden = self._forward(x)
            return (torch.argmax(logits, dim=-1), hidden)
        setattr(self, 'forward', preds)

    def eval(self):
        super().eval()
        setattr(self, 'forward', self._forward)

    def train(self, val=True):
        super().train(val)
        setattr(self, 'forward', self._forward)

    def save(self, filepath: Path):
        pass

    def load(self, filepath: Path):
        pass


class KHModel(HiddenLayerModel):
    """
    Model similar to that propsed by Krotov and Hopfield (KH)
    Architectural structure:
         FKHL3 (Fast Local Learning Layer)
           |
         PReLu (Polynomial ReLu)
           |
         Dense (Linear)
    """

    pSet = {}

    def __init__(self, *args): #ll_trained_state: dict):
        super().__init__()

        if len(args) != 1:
            raise IOError("'KHModel' constructor does not accept more than 1 argument")
        
        self.relu_h = nn.ReLU()
        self.relu_h.requires_grad_(False)

        self.softMax = nn.Softmax(dim=-1)

        if type(args[0]) is dict:
            trained_state = args[0]
            self.pSet = trained_state["fkhl3-state"]["model_parameters"]
            self.local_learning = FKHL3(self.pSet)

            self.dense = nn.Linear(self.pSet["hidden_size"], 10)
            self.dense.requires_grad_(True)

            #self.local_learning.load_state_dict(ll_trained_state["model_state_dict"])
            self.load_state_dict(trained_state["model_state_dict"])
        elif issubclass(type(args[0]), KHL3):
            self.local_learning = args[0]
            self.pSet = copy.deepcopy(self.local_learning.pSet)

            self.dense = nn.Linear(self.pSet["hidden_size"], 10)
            self.dense.requires_grad_(True)
        else:
            raise TypeError("'KHModel' constructor does not accept arguments of this type")

        self.local_learning.requires_grad_(False)


    def hidden(self, x: torch.Tensor) -> Tensor:
        return self.local_learning(x)

    def _forward(self, x: Tensor) -> Tensor:
        hidden = self.hidden(x)
        latent_activation = torch.pow(self.relu_h(hidden), self.pSet["n"])
        return (self.dense(latent_activation), hidden)


class SHLP(HiddenLayerModel):
    # single hidden layer perceptron model
    
    # default parameters
    pSet = {
        "in_size": 32*32*3,
        "hidden_size": 2000,
        "n": 4.5,
        "no_classes": 10,
    }
    
    def __init__(self, params: dict=None, sigma: float=None, dtype: torch.dtype=torch.float32, **kwargs):
        super(SHLP, self).__init__()
        if type(params) != type(None):
            self.pSet["in_size"] = params["in_size"]
            self.pSet["hidden_size"] = params["hidden_size"]
            self.pSet["n"] = params["n"]
            self.pSet["no_classes"] = params["no_classes"]
            
        self.dtype = dtype
        self.flatten = nn.Flatten()
        
        # define linear mapping between input and hidden layer
        # creating the representations
        # same fashion as in KHL3 for optimal control
        self.W = torch.zeros((self.pSet["in_size"], self.pSet["hidden_size"]), dtype=self.dtype)

        # if sigma not explicitely specified, use Keiming He initialisation scheme
        # from: He et al. (2015) "Delving Deep into Rectifiers: 
        # Surpassing Human-Level Performance on ImageNet Classification"
        if type(sigma) == type(None):
            sigma = math.sqrt(2 / self.pSet["in_size"])

        self.W.normal_(mean=0.0, std=sigma)
        self.W = nn.Parameter(self.W)
        
        self.ReLU = nn.ReLU()
        # define second mapping
        self.dense = nn.Linear(self.pSet["hidden_size"], self.pSet["no_classes"])
        
    def hidden(self, x: torch.Tensor):
        x_flat = self.flatten(x)
        return x_flat @ self.W
        
    def _forward(self, x: torch.Tensor):
        hidden = self.hidden(x)
        latent_activation = torch.pow(self.ReLU(hidden), self.pSet["n"])
        return self.dense(latent_activation), hidden


class SpecRegModel(SHLP):

    # default parameters
    pSet = {
        "in_size": 32*32*3,
        "hidden_size": 2000,
        "n": 4.5,
        "no_classes": 10,
        "nu": 10, # regularizing cutoff
    }

    def __init__(self, params: dict=None, sigma: float=None, dtype: torch.dtype=torch.float32, **kwargs):
        super(SpecRegModel, self).__init__(params=params, sigma=sigma, dtype=dtype, **kwargs)
        if type(params) != type(None):
            self.pSet["nu"] = params["nu"]


class IdentityModel(nn.Module):

    pSet = {
        "hidden_size": 2000,
    }
    
    def __init__(self, params: dict, **kwargs):
        super(IdentityModel, self).__init__()
        self.pSet["hidden_size"] = params["in_size"]
        self.flatten = nn.Flatten()
        
    def forward(self, x):
        return self.flatten(x)


def train_unsupervised(
    dataloader: DataLoader,
    model: KHL3,
    device: torch.device,
    filepath: Path,
    no_epochs=5,
    checkpt_period=1,
    learning_rate=None,
) -> None:
    """
    Unsupervised learning routine for a LocalLearningModel on a PyTorch 
    dataloader

    learning_rate=None - constant learning rate according to tau_l provided in model
    learning_rate=float - constant learning rate learning_rate
    learning_rate=function - learning according to the functional relation specified by learning_rate(epoch)
    """

    if type(learning_rate).__name__ != "function":

        if type(learning_rate).__name__ == "NoneType":
            learning_rate = 1.0 / model.pSet["tau_l"]

        lr = lambda l: learning_rate

    else:
        lr = learning_rate

    with torch.no_grad():
        with tqdm(range(1, no_epochs + 1), unit="epoch") as tepoch:
            #tepoch.set_description(f"Epoch: {epoch}")
            tepoch.set_description(f"Training time [epochs]")

            for epoch in tepoch:
                # catch lr(epoch) = 0 to avoid division by 0
                if lr(epoch) != 0.0:
                    # if learning rate == 0 -> no learning
                    model.pSet["tau_l"] = 1.0 / lr(epoch)
                    for batch_num, (features, labels) in enumerate(dataloader):
                        model.train_step(features.to(device))

                if epoch % checkpt_period == 0:
                    torch.save(
                        {
                            "model_parameters": model.param_dict(),
                            "model_state_dict": model.state_dict(),
                            "device_type": device.type,
                        },
                        filepath.parent
                        / Path(
                            str(filepath.stem) + "_" + str(epoch) + str(filepath.suffix)
                        ),
                    )


def train_half_backprop(
    dataloader: DataLoader,
    model: KHModel,
    device: torch.device,
    filepath: Path,
    no_epochs=5,
    checkpt_period=1,
    learning_rate=None,
) -> None:
    if type(learning_rate).__name__ != "function":

        if type(learning_rate).__name__ == "NoneType":
            learning_rate = 1.0 / model.pSet["tau_l"]

        learning_rate = lambda l: learning_rate

    def loss_fn(x: Tensor, labels: Tensor) -> float:
        return torch.mean(torch.pow(x - labels, m))

    optimizer = Adam(model.parameters(), lr=0.001)

    for epoch in range(1, no_epochs):

        cummulative_loss = 0.0
        with tqdm(dataloader, unit="batch") as tepoch:
            tepoch.set_description(f"Epoch: {epoch}")
            # for x, label in tepoch:
