# Distributed Multi-User Scrapy System with a Web UI

This is a Django project that lets users create, configure, deploy and run Scrapy spiders through a Web interface. The goal of this project is to build an application that would allow multiple users write their own scraping scripts and deploy them to a cluster of workers for scraping in a distributed fashion. The application allows the users do the following actions through a web interface:

  - Create a Scrapy project
  - Add/Edit/Delete Scrapy Items
  - Add/Edit/Delete Scrapy Item Pipelines
  - Edit Link Generator function (more on this below)
  - Edit Scraper function (more on this below)
  - Deploy the projects to worker machines
  - Start/Stop projects on worker machines
  - Display online status of the worker machines, the database, and the link queue
  - Display the deployment status of projects
  - Display the number of items scraped
  - Display the number of errors occured in a project while scraping
  - Display start/stop date and time for projects

# Architecture

The application comes bundled with Scrapy pipeline for MongoDB (for saving the scraped items) and Scrapy scheduler for RabbitMQ (for distributing the links among workers). The code for these were taken and adapted from https://github.com/sebdah/scrapy-mongodb and https://github.com/roycehaynes/scrapy-rabbitmq. Here is what you need to run the application: 
  - MongoDB server (can be standalone or a sharded cluster, replica sets were not tested)
  - RabbitMQ server
  - One link generator worker server with Scrapy installed and running scrapyd daemon
  - At least one scraper worker server with Scrapy installed and running scrapyd daemon

After you have all of the above up and running, fill sample_settings.py in root folder and  scrapyproject/scrapy_packages/sample_settings.py files with needed information, rename both files to settings.py, and run the Django server (don't forget to perform the migrations first). You can go to http://localhost:8000/project/ to start creating your first project.

# Link Generator

The link generator function is a function that will insert all the links that need to be scraped to the RabbitMQ queue. Scraper workers will be dequeueing those links, scraping the items and saving the items to MongoDB. The link generator itself is just a Scrapy spider written insde parse(self, response) function. The only thing different from the regular spider is that the link generator will not scrape and save items, it will only extract the needed links to be scraped and insert them to the RabbitMQ for scraper machines to consume.

# Scrapers

The scraper function is a function that will take links from RabbitMQ, make a request to that link, parse the response, and save the items to DB. The scraper is also just a Scrapy spider, but without the functionality to add links to the queue.

This separation of roles allows to distribute the links to multiple scrapers evenly. There can be only one link generator per project, and unlimited number of scrapers.

# RabbitMQ

When a project is deployed and run, the link generator will create a queue for the project in *username_projectname*:requests format, and will start inserting links. Scrapers will use RabbitMQ Scheduler in Scrapy to get one link at a time and process it. 

# MongoDB

All of the items that get scraped will be saved to MongoDB. There is no need to prepare the database or collections beforehand. When the first item gets saved to DB, the scraper will create a database in *username_projectname* format and will insert items to a collection named after the item's name defined in Scrapy. If you are using a sharded cluster of MongoDB servers, the scrapers will try to authoshard the database and the collections when saving the items. The hashed id key is used for sharding.

Here are the general steps that the application performs:
1. You create a new project, define items, define item pipelines, add link generator and scraper functions, change settings
2. Press Deploy the project
3. The scripts and settings will be put into a standard Scrapy project folder structure (two folders will be created: one for link generator, one for scraper)
4. The two folders will be packaged to .egg files
5. Link generator egg file will be uploaded to the scrapyd server that was defined in settings file
6. Scraper egg file will be uploaded to all scrapyd servers that were defined in settings file
7. You start the link generator
8. You start the scrapers

### Installation

The web application requires:
- Django 1.8.13 
- django-crispy-forms
- django-registration
- pymongo
- requests
- python-dateutil

On the link generator and scraper machines you need:
- Scrapy
- scrapyd
- pymongo
- pika

The dashboard theme used for the UI was retrieved from https://github.com/VinceG/Bootstrap-Admin-Theme. 

# Examples

Link generator and scraper functions are given in the examples folder.

# Screenshots

![Alt text](/screenshots/registration.png?raw=true "Registration page")
![Alt text](/screenshots/main_page.png?raw=true "Main page")
![Alt text](/screenshots/main_page_project.png?raw=true "Main page")
![Alt text](/screenshots/new_project.png?raw=true "New project")
![Alt text](/screenshots/manage_project.png?raw=true "Manage project")
![Alt text](/screenshots/additem.png?raw=true "Add item")
![Alt text](/screenshots/itemslist.png?raw=true "List of items")
![Alt text](/screenshots/addpipeline.png?raw=true "Add pipeline function")
![Alt text](/screenshots/pipelinelist.png?raw=true "List of pipeline functions")
![Alt text](/screenshots/addlinkgen.png?raw=true "Link generator")
![Alt text](/screenshots/addscraper.png?raw=true "Scraper")
![Alt text](/screenshots/deployment.png?raw=true "Project deployment")
![Alt text](/screenshots/main_page_scraped.png?raw=true "Main page")

# License

This project is licensed under the terms of the MIT license.
