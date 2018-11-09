# Checkout
A hardware checkout platform for TUDev

# setup

#### clone the repo

```git clone https://github.com/tudev/hackpack```

#### go to branch 3296

```git checkout 3296```

put the `env_vars_dev.sh` file in the `hackpack` directory

#### set the env variables

```source env_vars_dev.sh```

#### make sure python3 is installed and then install requirements
```pip3 install -r requirements.txt```

#### run the server
```python3 manage.py gunicorn```

#### go to URL (very important you go to exactly the same URL listed below)
```localhost:1337```

### login to the admin page by clicking on the sign into slack button in the top right corner
