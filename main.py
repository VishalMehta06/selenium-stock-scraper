from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import statistics as stat
import yfinance as yf
import os
import numpy as np

class Ticker():
    def __init__(self, ticker, name, historic_years):
        self.ticker = ticker
        self.name = name.replace(' ', '-')
        self.historic_years = historic_years

        # Current Price
        df = yf.download(tickers=self.ticker, period='2day')
        self.current_price = df['Close'].iloc[[-1]].max()

    def fcf_analysis(self, discount_rate, terminal_growth):
        # Set up input variables
        discount_rate = (discount_rate/100) + 1
        terminal_growth = (terminal_growth/100) + 1

        # Set up variables for timing and results 
        historic_fcf = pd.DataFrame(columns=['Year', 'FCF', 'FCF % Change'])

        # Start WebDriver for Firefox
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/free-cash-flow".format(self.ticker, self.name))

        # Scrape Historic Data
        for i in range(self.historic_years):
            add_year = 2022-i
            historic_fcf.loc[i] = ['%d'%add_year, float(driver.find_element(By.XPATH, "//div[@class='col-xs-6']/table/tbody/tr[{}]/td[2]".format(i+1)).text.replace(',', '')), 0]

        # Scrape Shares Outstanding Data
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/shares-outstanding".format(self.ticker, self.name))
        outstanding_shares = float(driver.find_element(By.XPATH, "//div[@class='col-xs-6']/table/tbody/tr/td[2]").text.replace(",", ""))

        # Reverse order of historic data and fill in FCF % Change
        historic_fcf = historic_fcf.iloc[::-1]
        for i in range(self.historic_years-1):
            num1 = float(historic_fcf['FCF'].loc[i])
            num2 = float(historic_fcf['FCF'].loc[i+1])
            historic_fcf['FCF % Change'].loc[i] = ((num1-num2)/abs(num2))*100
        
        # Decide Future FCF Growth
        fcf_change = list(historic_fcf['FCF % Change'])
        fcf_change.__delitem__(0)
        average_fcf_change = (abs(stat.mean(fcf_change)) / 100)

        num1 = historic_fcf['FCF'].iloc[[-1]].max()
        num2 = historic_fcf['FCF'].iloc[[0]].max()
        annualized_fcf = ((num1/num2)**((len(historic_fcf)-1))) -1

        if average_fcf_change < annualized_fcf and abs(average_fcf_change) <= 0.08:
            future_fcf_change = average_fcf_change + 1
        elif annualized_fcf < average_fcf_change and abs(annualized_fcf) <= 0.08:
            future_fcf_change = annualized_fcf + 1
        elif annualized_fcf > 0 and average_fcf_change > 0:
            future_fcf_change = 1.08
        else:
            future_fcf_change = -1.04
        

        #if average_fcf_change < annualized_fcf and abs(average_fcf_change) <= 0.08:
        #    future_fcf_change = average_fcf_change + 1
        #elif annualized_fcf < average_fcf_change and abs(annualized_fcf) <= 0.08:
        #    future_fcf_change = annualized_fcf + 1
        #else:
        #    future_fcf_change = 1.08

        # Set up variables to create future data (Future years = num_years - 1)
        future_fcf = pd.DataFrame(columns=['Year', 'FCF', 'FCF % Change','Value'])
        future_years = 9
        latest_fcf = historic_fcf['FCF'].iloc[[-1]].max()

        # Calculate Future Data
        for i in range(future_years+1):
            if future_fcf_change >= 0:
                add_fcf_change = (future_fcf_change-1)*100
                add_fcf = latest_fcf*future_fcf_change
            else:
                add_fcf_change = (future_fcf_change+1)*100
                add_fcf = abs(latest_fcf)*future_fcf_change
            add_year = 2023 + i
            add_price = add_fcf/(discount_rate**(add_year - 2022))

            future_fcf.loc[i] = ['%d'%add_year, add_fcf, add_fcf_change, add_price]

            # Reset the last FCF value to compound growth
            latest_fcf = add_fcf
        
        # Calculate Intrinsic Value
        future_value_sum = 0
        for i in range(len(future_fcf)):
            future_value_sum += future_fcf['Value'].iloc[[i]].max()
        terminal_value = (future_fcf['FCF'].iloc[[-1]].max() * terminal_growth)/(discount_rate-terminal_growth)
        current_terminal_value = terminal_value/(discount_rate ** 10)
        
        future_value_sum += current_terminal_value
        intrinsic_value = future_value_sum / outstanding_shares

        # Safety Margin
        safety_margin = ((intrinsic_value - self.current_price) / self.current_price) * 100

        # Record Results
        self.fcf_historic_data = historic_fcf
        self.fcf_future_data = future_fcf
        self.fcf_intrinsic_value = intrinsic_value
        self.fcf_safety_margin = safety_margin

    def eps_analysis(self):
        # Declare Variables for gathering historic data
        historic_eps = pd.DataFrame(columns=['Year', 'EPS'])  
        historic_pe = []

        # Open Driver and URL
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/eps-earnings-per-share-diluted".format(self.ticker, self.name))
        
        # Scrape Historic EPS
        for i in range(self.historic_years):
            add_year = (2023 - self.historic_years) + i
            historic_eps.loc[i] = ['%d'%add_year, float(driver.find_element(By.XPATH, "//table[@class='historical_data_table table']/tbody/tr[{}]/td[2]".format(self.historic_years-i)).text.replace(',', '').replace('$', ''))]
        
        # Scrape Historic PE
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/pe-ratio".format(self.ticker, self.name))
        for i in range(self.historic_years*4):
            try:
                historic_pe.append(float(driver.find_element(By.XPATH, "//div[@id='main_content']/div[8]/table/tbody/tr[{}]/td[4]".format(i+1)).text.replace(',', '')))
            except:
                break
        # Calculate Average PE
        average_pe = sum(historic_pe)/len(historic_pe)

        # Declare variables for future EPS and PE prices
        future_eps = pd.DataFrame(columns=['Year', 'EPS', 'Price'])
        latest_eps = historic_eps['EPS'].iloc[[-1]].max()

        # Find EPS Growth
        num1 = historic_eps['EPS'].iloc[[-1]].max()
        num2 = historic_eps['EPS'].iloc[[0]].max()
        if num1/num2 < 0:
            eps_growth = round(-(abs(num1/num2)**(1/self.historic_years)), 5)
        else:
            eps_growth = round((num1/num2)**(1/self.historic_years), 5)
        
        # Calculate Future EPS
        for i in range(10):
            add_year = 2023 + i
            if eps_growth < 0:
                add_eps = round(-(abs(latest_eps) * abs(eps_growth)), 2)
            else:
                add_eps = round((abs(latest_eps) * eps_growth), 2)
            add_price = round(add_eps * average_pe, 2)
            future_eps.loc[i] = ['%d'%add_year, add_eps, add_price]

            latest_eps = add_eps
        
        self.eps_historic = historic_eps
        self.eps_future = future_eps
        self.pe_average = average_pe
        self.eps_growth_rate = (eps_growth-1)*100
        self.eps_five_year_value = future_eps['Price'].iloc[[4]].max()
        self.eps_ten_year_value = future_eps['Price'].iloc[[9]].max()
    
    def print_out(self):
        os.system('cls')
        print("-----------------------------------------------------------------------------------------------------------------")
        print("RESULTS\n\n")

        # Basic:
        # Stock Ticker
        print(self.ticker)
        # Current Price
        print("${}".format(self.current_price))

        # Required:
        # Intrinsic Value
        print("\n\nFCF Intrinsic Value:  ${}".format(round(self.fcf_intrinsic_value, 2)))
        # Safety Margin
        print("FCF Safety Margin:  {}%\n".format(round(self.fcf_safety_margin, 3)))

        # EPS Growth
        print("EPS Growth Rate:  {}%".format(round(self.eps_growth_rate, 3)))
        # Average PE
        print("Average PE:  {}".format(round(self.pe_average, 3)))
        # 5 year Growth
        print("EPS 5 Year Movement:  ${}".format(round(self.eps_five_year_value, 3)))
        # 10 year Growth
        print("EPS 10 Year Movement:  ${}\n".format(round(self.eps_ten_year_value, 3)))

        # Extra:
        # Historic FCF
        print("FCF Historic Data:  \n{}".format(self.fcf_historic_data))
        # Future FCF
        print("FCF Future Data:  \n{}".format(self.fcf_future_data))

        # Historic EPS
        print("\nEPS Historic Data:  \n{}".format(self.eps_historic))
        # Future EPS
        print("EPS Future Data:  \n{}".format(self.eps_future))

while True:
    os.system('cls')
    print("-----------------------------------------------------------------------------------------------------------------")
    print("LONG TERM INVESTING\n\n")
    stock_action_choice = input(" (1) Input Stock\n (2) Use Stock Lists\n (3) Edit a Stock List\n (4) Create New Stock List\n (5) Exit App\n\n:  ")
    if stock_action_choice == '1':
        stock = Ticker(input("\nTicker:  ").upper(), input("\nName:  ").lower().replace(" ", "-"), int(input("\nTime Past:  ")))
        driver = webdriver.Firefox()
        stock.fcf_analysis(8, 2)
        stock.eps_analysis()
        stock.print_out()
        driver.close()
        input(":  ")

    elif stock_action_choice == '2':
        stock_list_name = input('\nList Name:  ').lower()
        stock_list = pd.read_csv(stock_list_name)
        results = pd.DataFrame(columns=['Ticker', 'Current Price','Intrinsic Value (FCF)', 'Safety Margin (FCF)', 'Historic EPS Growth', 'Average PE', '5 Year Price (EPS)', '10 Year Price (EPS)'])
        driver = webdriver.Firefox()
        
        for i in range(len(stock_list)):
            stock = Ticker(stock_list['Ticker'].loc[i], stock_list['Name'].loc[i], stock_list['Years Past'].loc[i])
            print(stock.ticker)
            stock.fcf_analysis(8, 2)
            stock.eps_analysis()

            results.loc[i] = [stock.ticker, stock.current_price,stock.fcf_intrinsic_value, stock.fcf_safety_margin, stock.eps_growth_rate, stock.pe_average, stock.eps_five_year_value, stock.eps_ten_year_value]

        driver.close()

        list_save_choice = input('{}\n\nDo you want to save results (y/n):  '.format(results)).lower()
        while True:
            if list_save_choice == 'y':
                results.to_csv('results.csv')
                break
            elif list_save_choice == 'n':
                print(results.to_csv())
                input("The CSV anyways:  ")
                break
            

    elif stock_action_choice == '3':
        os.system('cls')
        print("-----------------------------------------------------------------------------------------------------------------")
        print("EDIT A STOCK LIST\n\n")
        edit_list_name = input('Enter List Name:  ').lower()
        try:
            edit_stocks = pd.read_csv(edit_list_name)
            edit_stocks_correct = True
        except:
            print('Incorrect Stock List Name')
            edit_stocks_correct = False
            input(":  ")
            pass
        
        while edit_stocks_correct == True:
            os.system('cls')
            print("-----------------------------------------------------------------------------------------------------------------")
            print("EDIT A STOCK LIST\n\n")
            
            row_edit = input("{}\n\nRow to Edit (Submit blank to stop adding stocks):  ".format(edit_stocks))
            if row_edit == "":
                break
            os.system('cls')
            stock_edit_ticker = input('{}\n\nTicker:  '.format(edit_stocks.iloc[[int(row_edit)]]))
            stock_edit_name = input('\nName:  ')
            stock_edit_years = int(input('\nYears Past:  '))
            edit_stocks['Ticker'].loc[int(row_edit)], edit_stocks['Name'].loc[int(row_edit)], edit_stocks['Years Past'].loc[int(row_edit)] = stock_edit_ticker, stock_edit_name, stock_edit_years

        while edit_stocks_correct == True:
            os.system('cls')
            print("-----------------------------------------------------------------------------------------------------------------")
            print("EDIT A STOCK LIST\n\n")
            list_save_choice = input('{}\n\nDo you want to save the list you made (y/n):  '.format(edit_stocks)).lower()
            if list_save_choice == 'y':
                edit_stocks.to_csv(edit_list_name)
                break
            elif list_save_choice == 'n':
                print(edit_stocks.to_csv())
                input("The CSV anyways:  ")
                break

    elif stock_action_choice == '4':
        stocks = pd.DataFrame(columns=['Ticker', 'Name', 'Years Past'])
        while True:
            os.system('cls')
            print("-----------------------------------------------------------------------------------------------------------------")
            print("CREATE A STOCK LIST\n\n")
            stock_add_ticker = input('{}\n\nTicker (Submit blank to stop adding stocks):  '.format(stocks))
            if stock_add_ticker == "":
                os.system('cls')
                break
            stock_add_name = input('\nName:  ')
            stock_add_years = int(input('\nYears Past:  '))

            stocks.loc[len(stocks)] = [stock_add_ticker, stock_add_name, stock_add_years]
        
        while True:
            print("-----------------------------------------------------------------------------------------------------------------")
            print("CREATE A STOCK LIST\n\n")
            list_save_choice = input('{}\n\nDo you want to save the list you made (y/n):  '.format(stocks)).lower()
            if list_save_choice == 'y':
                stocks.to_csv(input('\nList Name:  ').lower())
                break
            elif list_save_choice == 'n':
                print(stocks.to_csv())
                break
    
    elif stock_action_choice == '5':
        os._exit(0)




# Set up variables
#results = pd.DataFrame(columns=['Ticker', 'FCF Intrinsic Value', 'FCF Safety Margin'])
#stock_list = pd.read_csv('stock_names.csv')

# Run Tests
#for i in range(len(stock_list)):
    # Create Object
#    stock = Ticker('{}'.format(stock_list['Ticker'].loc[i]), '{}'.format(stock_list['Name'].loc[i]))

    # Run Analysis
#    stock.fcf_analysis(stock_list['Years Past'].iloc[[i]].max(), 1.08, 1.02)

    # Print Completion Message
#    print("\n--------------- {}% Complete ---------------".format(round(((i+1)/len(stock_list))*100, 2)))

    # Save Results
#    results.loc[i] = [stock.ticker, round(stock.fcf_intrinsic_value, 2), round(stock.fcf_safety_margin, 2)]

#print("\nRESULTS")
#results.sort_values('FCF Safety Margin', inplace=True, ascending=False)
#print(results)

#while True:
#    save_choice = input('Save Results (y/n)?  ')
#    if save_choice == 'y':
#        results.to_csv('results.csv')
#        break
#    elif save_choice == 'n':
#        print("\n")
#        print(results.to_csv())
#        break

#stock = Ticker('AAPL', 'apple', 10)
#stock.fcf_analysis(8, 2)
#stock.eps_analysis()

#print(stock.eps_historic)
#print("")
#print(stock.eps_future)
#print("")
#print("Average PE:  {}".format(stock.pe_average))
#print("EPS Growth:  {}".format(stock.eps_growth_rate))
#print("5 Year Growth:  {}".format(stock.eps_five_year_growth))
#print("10 Year Growth:  {}".format(stock.eps_ten_year_growth))

#print(stock.fcf_historic_data)
#print(stock.fcf_future_data)
#print(stock.fcf_intrinsic_value)
#print(stock.fcf_safety_margin)