from datetime import datetime
import requests
import textwrap
from tabulate import tabulate
from configparser import ConfigParser, NoSectionError, NoOptionError
import yaml
import os
import csv
import sys

class ConfigHandler:

    def __init__(self, config_type):
        self.config_type = config_type

    def get_config(self, section, option, config_type):
        if config_type == 'ini':
            parser = ConfigParser()
            parser.read('config.ini')
            try:
                return parser.get(section, option)
            except FileNotFoundError:
                print('Missing Configuration file')
                sys.exit(1)
            except NoSectionError:
                print(f'Missing section {section} in config.ini')
                sys.exit(1)
            except NoOptionError:
                print(f'Missing option {option} in config.ini')
                sys.exit(1)
        elif config_type == 'yaml':
            file = open('config.yaml')
            config = yaml.safe_load(file)
            try:
                return config[section][option]
            except FileNotFoundError:
                print('Missing Configuration file')
                sys.exit(1)
            except KeyError:
                print(f'Missing field {option} in config.yaml')
                sys.exit(1)


class Validator(ConfigHandler):

    def input_validation(self, text, choice_list):
        while True:
            choice = input(text)
            if choice in choice_list:
                return choice
            else:
                print('Invalid choice. Please enter again')


    def capture_decision(self, purpose):
        while True:
            decision = input(f'Do you want to enter {purpose}(y/n): ')
            if decision in ['y', 'Y']:
                return True
            elif decision in ['n', 'N']:
                return False
            else:
                print(f'Invalid Selection. please select again')


    def valid_date_range(self, date):
        today = datetime.today()
        diff = (today-date).days
        return diff


    def get_date(self, config_type):
         fmt = self.get_config('everything_params', 'date_format', config_type)
         date_fmt = ''
         for ele in fmt.split('-'):
             date_fmt = date_fmt + '%'+ele + '-'
         return date_fmt[:-1]


    def valid_date(self, text, config_type):
        while True:
            date = input(text)
            try:
                data = datetime.strptime(date, self.get_date(config_type))
                if self.valid_date_range(data) > 30:
                    print('Date range exceed. Please enter again')
                else:
                    return date
            except ValueError:
                print('Invalid date. please enter again')


    def gen_dict(self, info):
        dt = {}
        for i in range(len(info)):
            dt[str(i + 1)] = info[i]
        return dt


    def selection(self, section, val, config_type):
        if config_type == 'ini':
            sort_value = self.get_config(section, val, config_type).split(',')
        elif config_type == 'yaml':
            sort_value = self.get_config(section, val, config_type)
        dt = self.gen_dict(sort_value)
        return dt


class OutputHandler:

    def tabular_form(self, data, output_type):
        if isinstance(data, dict) and len(['articles']) > 0:
            li = []
            for article in data['articles']:
                if article['author'] is None or article['author'] == '':
                    author = 'No Author'
                else:
                    author = article['author']
                trimmed_title = textwrap.fill(str(article['title']), width=25)
                trimmed_description = textwrap.fill(str(article['description']), width=25)
                li.append([author, trimmed_title, trimmed_description, article['publishedAt']])
            if output_type == 'console':
                print(tabulate(li, headers=['Author', 'Title', 'Description', 'PublishedAt'], tablefmt='fancy_grid'))
            elif output_type == 'file_txt':
                filepath = 'table.txt'
                if os.path.exists(filepath):
                    file_mode = 'a'
                else:
                    file_mode = 'w'
                file = open(filepath, file_mode, encoding='utf-8')
                file.write(tabulate(li, headers=['Author', 'Title', 'Description', 'PublishedAt'], tablefmt='fancy_grid'))
                file.close()
                if file_mode == 'w':
                    print('File created successfully')
                if file_mode == 'a':
                    print('File updated successfully')
            elif output_type == 'csv':
                if len(data['articles']) > 0:
                    filepath = input('Enter file name with .csv extension: ')
                    file = open(filepath, 'w', encoding='utf-8-sig')
                    headings = ['Author', 'Title', 'Description', 'PublishedAt']
                    csv_write = csv.writer(file)
                    csv_write.writerow(headings)
                    csv_write.writerows(li)
                    file.close()
                    print(f'File created successfully with the name {filepath}')
                else:
                    print('No articles to write to csv')
        else:
            print('No results found')


class NewsApp(Validator):

    def __init__(self, output_type, config_type):
        self.output_type = output_type
        self.config_type = config_type
        self.output = OutputHandler()

    def api_call(self, url, params):
        response = requests.get(url, params = params)
        if response.status_code == 200:
            return response.json()
        else:
            return f'Error while making the request| status code: {response.status_code} | reason : {response.reason}'

    def get_user_selection(self, section, param_name, config_type):
        options = self.selection(section,param_name, config_type)
        for key, val in options.items():
            print(f'{key}: {val}')
        user_choice = self.input_validation(text=f'Enter your choice for {param_name}: ', choice_list=options.keys())
        return options[user_choice]


    def everything_endpoint(self, config_type, output_type):
        print('You have selected everything API')
        query = input('Enter your search query: ')
        search_in, sort_by, from_date_obj, to_date_obj, language = None, None, None, None, None
        if self.capture_decision('search') is True:
            search_in = self.get_user_selection('everything_params','searchIn', config_type)

        if self.capture_decision('sort') is True:
            sort_by = self.get_user_selection('everything_params','sortBy', config_type)

        if self.capture_decision('dates') is True:
            from_date_obj = self.valid_date(text='Enter from date(YYYY-MM-DD): ',config_type=config_type)
            to_date_obj = self.valid_date(text='Enter to date(YYYY-MM-DD): ',config_type=config_type)

        if self.capture_decision('language') is True:
            language = self.get_user_selection('everything_params','language', config_type)

        params = {'q': query, 'apikey': self.get_config('settings', 'api_key', config_type), 'sortBy': sort_by, 'searchIn': search_in, 'from': from_date_obj, 'to': to_date_obj, 'language': language }
        response = self.api_call(url=self.get_config('settings', 'base_url_everything', config_type), params=params)
        self.output.tabular_form(data=response, output_type= output_type)


    def top_headlines_endpoint(self, config_type, output_type):
        print('You have selected Top headlines API')
        query, category, country = None, None, None
        if self.capture_decision('query'):
            query = input('Enter your search query: ')

        if self.capture_decision('category') is True:
            category = self.get_user_selection('top_headlines_params', 'category', config_type)

        if self.capture_decision('country') is True:
            country = self.get_user_selection('top_headlines_params', 'country', config_type)

        params = {'q': query, 'apikey': self.get_config('settings', 'api_key', config_type), 'category': category,
                  'country': country}
        response = self.api_call(url=self.get_config('settings', 'base_url_top_headlines', config_type), params=params)
        self.output.tabular_form(data=response, output_type=output_type)

class Main:

    def run(self):
        print('Welcome to NEWS Channel')
        print('Select Configuration file','1. INI file', '2. YAML file', sep='\n')
        app = NewsApp('config_type', 'output_type')
        config_choice = app.input_validation(text='Choose an option: ', choice_list=['1','2'])
        if config_choice == '1':
            config_type = 'ini'
        elif config_choice == '2':
            config_type = 'yaml'

        print('Select Data output format','1. console', '2. file_txt','3. csv', sep='\n')
        output_selection = app.input_validation(text='Choose an option: ', choice_list=['1','2','3'])
        if output_selection == '1':
            output_type = 'console'
        elif output_selection == '2':
            output_type = 'file_txt'
        elif output_selection == '3':
            output_type = 'csv'
        print('1. Everything', '2. Top headlines', sep='\n')
        choice = app.input_validation(text='Choose an option: ', choice_list=['1','2'])
        if choice == '1':
            app.everything_endpoint(config_type, output_type)

        elif choice == '2':
            app.top_headlines_endpoint(config_type, output_type)

n = Main()
n.run()


