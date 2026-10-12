# Optional CPU neural environment

The demo and rate/logistic/BKT baseline environment does not require PyTorch.
Install the separate CPU lockfile when working on LSTM research:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock -r requirements-neural.lock
```

The PyTorch wheel comes from its official CPU index and is pinned with the other
backend dependencies. `pip install '.[neural]'` expresses compatibility but uses
the platform's normal package indexes; use the lockfile above for the tested CPU
configuration. See [official installation guidance](https://pytorch.org/get-started/locally/).

CPU neural CI installs this environment, asserts a CPU backend and runs all
tests with one numerical-library thread. General CI remains lightweight; neural
tests use `pytest.importorskip("torch")` there and must pass in the dedicated
backend job before rollout. Installing an environment is not a trained model or
empirical result; no GPU, student data or pretrained encoder is downloaded here.
