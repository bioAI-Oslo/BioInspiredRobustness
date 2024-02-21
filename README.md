# LocalLearning
Exploring mechanisms of Neural Robustness: probing the bridge between geometry and spectrum.

# License
This project contains code under both the MIT License and the Apache License 2.0.
Apart from the explicitely marked sections, this project is published under the MIT License 
under the following copyright.

Copyright (c) 2024 Konstantin Holzhausen and University of Oslo

---

Code in the file `src/LocalLearning/LocalLearning.py` is entirely under the Apache License 2.0 under the following copyrights.

Copyright (c) 2018 Dmitry Krotov

PyTorch implementation and further modifications:  
Copyright(c) 2024 Konstantin Holzhausen and University of Oslo

Parts are a PyTorch implementation based on Dmitry Krotov's Biological Learning described in [1]  
repository: https://github.com/DimaKrotov/Biological_Learning  
commit: 45478bb8143cc6aa3984c040dfd1bc8bc44e4e29  

---

A section in the file `src/LocalLearning/Regularizers.py` is under the MIT License under the following copyright.

Copyright (c) Facebook, Inc. and its affiliates.

It contains a modified version of the PyTorch implementation of Jacobian regularization described in [2].  
repository: https://github.com/facebookresearch/jacobian_regularizer  
commit: 32bb044c4c0163c908ef3c166d07d4ab2a248e07  


Another section contains a modified version of the PyTorch implementation of Spectral Regularization described in [3].
In addition, the regularizer design principle was heavily influenced by Josua Nassar's code.  
repository: https://github.com/josuenassar/power_law  
commit: 13f8f36f9cbe57a22fd5a5f7f2c7a73c1f322671  


# References
[1] Dmitry Krotov and John J. Hopfield, "Unsupervised learning by competing hidden units.", 2019.  
    PNAS, Vol. 116, No. 16 [doi](https://doi.org/10.1073/pnas.1820458116)  

[2] Judy Hoffman, Daniel A. Roberts, and Sho Yaida,  
    "Robust Learning with Jacobian Regularization.", 2019.  
    [arxiv:1908.02729](https://arxiv.org/abs/1908.02729)  

[3] Josue Nassar, "On 1/n neural representation and robustness.",   
    Advances in Neural Information Processing Systems., 33.  
    [pdf](https://proceedings.neurips.cc/paper/2020/file/44bf89b63173d40fb39f9842e308b3f9-Paper.pdf)  


# Using CPU: Docker Container
```bash
sudo chown 1000:1000 LocalLearning/src
sudo chown 1000:1000 LocalLearning/notebooks
sudo chwon 1000:1000 LocalLearning/data
docker build -t pytorch-cpu-dev .
docker run -v $PWD:/pytorch-dev/LocalLearning -p 3108:3108 -it pytorch-cpu-dev
```
# Using GPU: Anaconda virtual environment
```bash
conda env create -f pytorch.yml
```

# Reproducibility
Figures, model files and experimental results are found in
```bash
├── data
│   ├── models
|   |   ├── ...
│   ├── figures
|   |   ├──...
│   ├── experiments
|   |   ├──...
```


To reproduce results and create another sample, run
```bash
python ./src/create_repro.py
```
which creates the directory structure for reproduction and runs 
two python scripts, equivalent to
```bash
python ./src/llearn_CIFAR.py ../data/repro/models/fkhl3_cifar10.pty &&
python ./src/prune_and_plot_FKHL3_CIFAR.py ../data/repro/models/fkhl3_cifar10.pty ../data/repro/figures
```
. The first one learns and saves Krotov and Hopfield's local learning layer. 
The second one executes pruning of weights if necessary, creates Figure A1 and saves it.
This results in the following files in data.
```bash
├── data
│   ├── models
|   |   ├── ...
│   ├── figures
|   |   ├── ...
│   ├── experiments
|   |   ├── ...
|   ├── repro
|   |   ├── models
|   |   |   ├── fkhl3_cifar10.pty
|   |   |   ├── fkhl3_cifar10_pruned.pty
|   |   ├── figures
|   |   |   ├── FigureA1-FKHL3Spectra.eps
|   |   ├── experiments
```
At this point, the Jupyter notebooks in /notebooks can be run the following order
to recreate all models, experimental result files and figures.
- Training_CIFAR10.ipynb
- Figure1-FigureA2-AdversarialAttacks.ipynb
- Figure2-Figure3-SpectralProbing.ipynb
- Figure4-DecisionBoundaries.ipynb