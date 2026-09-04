import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*starlette.testclient.*")
warnings.filterwarnings("ignore", message=".*httpx2.*")
warnings.filterwarnings("ignore")

