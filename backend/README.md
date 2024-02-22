# backend - the Python tools and API for SpExoDisks

You need add the data folder to the backend folder. 
You can do this by running the following command in the backend folder:
```
cd backend
git clone https"//github.com/spexod/data
```

### Installing dependencies

Create either your [Python environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) or [Anaconda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html). 

run `pip install -r requirements.txt`to install required packages.

Once packages have been installed, type `python manage.py runserver` in either your terminal or CMD to run the server.

After starting the server, you can view the API at:
<http://localhost:8000/api/>

Note - if Django is asking for migrations use (Structure is already completed):
> python manage.py migrate --fake 

Or if you have models that have been modified/added use:
> python manage.py makemigrations
> python manage.py migrate
