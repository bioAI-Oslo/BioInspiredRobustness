import os, sys
from pathlib import Path
import torch
from torchvision.transforms import ToTensor
from LocalLearning import FKHL3
from LocalLearning.Data import LpUnitCIFAR10
from LocalLearning.Data import DeviceDataLoader
from LocalLearning import train_unsupervised
from LocalLearning import weight_convergence_criterion
from LocalLearning import weight_mean_criterion

# Model parameters

model_ps = {
    "in_size": 3 * 32 ** 2,
    "hidden_size": 2000,
    "n": 4.5,
    "p": 3.0,
    "tau_l": 1.0 / 0.02,  # 1 / learning rate
    "k": 2,
    "Delta": 0.4,  # inhibition rate
    "R": 1.0,  # asymptotic weight norm radius
}

# Unsupervised Training Hyperparameters
NO_EPOCHS = 1000
BATCH_SIZE = 1000

if __name__ == "__main__":
    '''
    Learns Krotov and Hopfield's local learning layer on CIFAR10 data in an 
    unsupervised fashion.

    ARGS: 
        <modelpath> (string):   path including file name to save the model to after training
    '''

    if len(sys.argv) != 2:
        print("usage: python train_CIFAR.py <modelpath>")
        os._exit(os.EX_USAGE)

    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    model_path = Path(sys.argv[1])
    if not os.path.exists(model_path.parent):
        os.makedirs(model_path.parent)

    model = FKHL3(model_ps, sigma=1.0)
    model.to(device=device)

    training_data = LpUnitCIFAR10(
            root="../data/CIFAR10", train=True, transform=ToTensor(), p=model_ps["p"]
    )

    dataloader_train = DeviceDataLoader(
            training_data, device=device, batch_size=BATCH_SIZE, num_workers=4, shuffle=True
    )

    lr = 1.0 / model_ps["tau_l"] 
    def learning_rate(epoch: int) -> float:
        return (1.0 - epoch / NO_EPOCHS) * lr

    train_unsupervised(
        dataloader_train,
        model,
        device,
        model_path,
        no_epochs=NO_EPOCHS,
        checkpt_period=NO_EPOCHS,
        learning_rate=learning_rate,
    )

    # check convergence criteria
    # weights converge towards 1.0
    if not weight_convergence_criterion(model, 1e-2, 1e-1):
        print("Less than 10pc of weights converged close enough. Model not saved. Try running again.")
        os._exit(os.EX_OK)

    if not weight_mean_criterion(model):
        print("Weights converged to the wrong attractor. Model not saved. Try running again.")
        os._exit(os.EX_OK)  


    torch.save(
        model.state_dict(),
        model_path,
    )
