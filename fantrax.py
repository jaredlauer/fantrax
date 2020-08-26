from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import os

def browser_setup(home_directory):
    # Sets default download folder
    chromeOptions = webdriver.ChromeOptions()
    download_folder = home_directory
    prefs = {"download.default_directory" : download_folder}
    chromeOptions.add_experimental_option("prefs", prefs)
    # Starts browser instance with custom settings for download folder
    browser = webdriver.Chrome(options = chromeOptions)
    # Tells the browser to wait up to 10 seconds when searching for elements, every time
    browser.implicitly_wait(10)
    # Important to maximize broswer window so all page elements are loaded
    browser.maximize_window()
    return browser
def login(browser, login_credentials_filepath):
    url_login = 'https://www.fantrax.com/login'
    username_textbox_id = 'mat-input-0'
    password_textbox_id = 'mat-input-1'
    login_button_xpath = '/html/body/app-root/div/div[2]/div/app-login/div/section/form/div[2]/button'

    # Navigate to login page
    browser.get(url_login)

    with open(login_credentials_filepath) as f:
        username = f.readline()
        password = f.readline()

    try:
        input_username = browser.find_element_by_id(username_textbox_id)
        input_username.send_keys(username)
    except NoSuchElementException:
        print("Could not find username entry field")
        pass

    try:
        input_password = browser.find_element_by_id(password_textbox_id)
        input_password.send_keys(password)
    except NoSuchElementException:
        print("Could not find password entry field")
        pass

    try:
        login_button = browser.find_elements_by_xpath(login_button_xpath)
        login_button[0].click()
    except NoSuchElementException:
        print("Could not find login button")
        pass
def navigate_to_team_page(browser, url_team_page):
    period_select_id = 'mat-select-2'
    url = url_team_page
    browser.get(url)
    #time.sleep(1) # Pause to allow page to load

def download_team_roster(browser, team_roster_filepath):
    browser.get('https://www.fantrax.com/fantasy/league/qyfm7iiajx6nt5tq/team/roster')
    #time.sleep(3)
    # Delete old roster to prevent duplicates with (1), (2), etc.
    if os.path.exists(team_roster_filepath):
        os.remove(team_roster_filepath)
        print("Old roster deleted")

    download_team_roster_button_xpath = '/html/body/app-root/div/div[2]/div/app-league-team-roster/div/section/filter-panel/div/div[4]/div[2]/button[4]/span/mat-icon'

    try:
        download_team_roster_button = browser.find_elements_by_xpath(download_team_roster_button_xpath)
        download_team_roster_button[0].click()
    except NoSuchElementException:
        print("Could not find team roster download button")
        pass

    timeout = 300 # seconds
    timeout_start = time.time()

    while time.time() < timeout_start + timeout:
        if os.path.exists(team_roster_filepath):
            print("Team Roster download successful")
            break
        else:
            time.sleep(1)
def import_team_roster_from_csv(team_roster_filepath):
    # Creates pandas dataframe from csv, stripping top two rows to clear headers
    df = pd.read_csv(team_roster_filepath, header = None, skiprows = [0,1])

    # Returns index for end of skater list as an integer, by looking for the word 'Totals' in the first column
    end_of_skater_list_index = df[df[0] == 'Totals'].index.values.astype(int)[0]

    # Slices data frame to only include skaters
    df_skaters = df[:end_of_skater_list_index]
    # Adds column headers for skaters
    df_skaters.columns = ["Position", "Player", "Team", "Eligible", "Status", "Age", "Opponent", "Salary", "GP", "G", "A", "Pt", "+/-", "SOG", "STP", "H+B", "GWG+"]

    # Slices data frame to only include goalies
    df_goalies = df[end_of_skater_list_index+3:-1]
    # Resets row indexes to start from 0, drop = True drops extra column created by method
    df_goalies = df_goalies.reset_index(drop = True)
    # Removes extra columns
    df_goalies = df_goalies.drop(df_goalies.columns[[13, 14, 15, 16]], axis = 1)
    # Adds column headers for goalies
    df_goalies.columns = ["Position", "Player", "Team", "Eligible", "Status", "Age", "Opponent", "Salary", "GP", "W", "GAA", "SV%", "SHO"]

    print("Skaters: \n", df_skaters)
    print("Goalies: \n", df_goalies)

    return df_skaters, df_goalies
def create_move_list(df):
    # Creates data frame of inactive players with a game that day
    df_sub_in = df[(df['Status'] == 'Res') & df['Opponent'].notnull()]
    # df_sub_in = df[(df['Status'].isin(['Res', 'Min']) & df['Opponent'].notnull())]
    # Creates data frame of active players with no game that day
    df_sub_out = df[(df['Status'] == 'Act') & df['Opponent'].isnull()]

    print("In: \n", df_sub_in)
    print("Out: \n", df_sub_out)

    move_list = {}

    # Creates list of all possible substitutions for each player
    for index_in, row_in in df_sub_in.iterrows():
        out_list = []
        for index_out, row_out in df_sub_out.iterrows():
            if row_out['Position'] in row_in['Eligible']:
                out_list.append(index_out)
            move_list[index_in] = out_list

    move_list = simplify_move_list(move_list)
    print(move_list)
    return move_list
def simplify_move_list(move_list):
    # To sort list by length of values in key:value pair
    # sorted_move_list = sorted(move_list.items(), key = lambda x: len(x[1]))

    used_numbers_list = []
    new_move_list = {}
    for key, value in move_list.items():
        counter = 0
        for item in value:
            if counter < len(value):
                if item not in used_numbers_list:
                    used_numbers_list.append(item)
                    new_move_list[key] = item
                    break
                else:
                    counter += 1
    return new_move_list
def convert_move_list_to_xpath(skater_move_list, goalie_move_list):
    xpath_move_list = {}

    for key, value in skater_move_list.items():
        player_in_button_xpath = generate_skater_roster_button_xpath(int(key))
        player_out_button_xpath = generate_skater_roster_button_xpath(int(value))
        xpath_move_list[player_in_button_xpath] = player_out_button_xpath

    for key, value in goalie_move_list.items():
        player_in_button_xpath = generate_goalie_roster_button_xpath(int(key))
        player_out_button_xpath = generate_goalie_roster_button_xpath(int(value))
        xpath_move_list[player_in_button_xpath] = player_out_button_xpath

    print(xpath_move_list)
    return xpath_move_list
def generate_skater_roster_button_xpath(index):
    first_part = '/html/body/app-root/div/div[2]/div/app-league-team-roster/div/section/div[3]/ultimate-table/div/section/aside/td['
    second_part = ']/button'
    # Add one to index because Fantrax uses one based indexing
    xpath = first_part + str(index+1) + second_part

    return xpath
def generate_goalie_roster_button_xpath(index):
    first_part = '/html/body/app-root/div/div[2]/div/app-league-team-roster/div/section/div[4]/ultimate-table/div/section/aside/td['
    second_part = ']/button'

    xpath = first_part + str(index+1) + second_part

    return xpath
def execute_move_list(browser, move_list):
    for player_in_button_xpath, player_out_button_xpath in move_list.items():
        try:
            player_in_button = browser.find_elements_by_xpath(player_in_button_xpath)
            player_in_button[0].click()
        except NoSuchElementException:
            print("Could not find player in button")
            pass

        try:
            player_out_button = browser.find_elements_by_xpath(player_out_button_xpath)
            player_out_button[0].click()
        except NoSuchElementException:
            print("Could not find player out button")
            pass

    roster_submit_button_xpath = '/html/body/app-root/div/layout-overlay/overlay-toasts/toast[2]/section/div[1]/button[2]/span'
    try:
        roster_submit_button = browser.find_elements_by_xpath(roster_submit_button_xpath)
        roster_submit_button[0].click()
    except NoSuchElementException:
        print("Could not find roster submit button")
        pass

    # The last two objects in this function don't appear every time so I added a check to make sure there is a non-empty array
    # returned before they are clicked to avoid an IndexError
    apply_to_future_periods_checkbox_id = 'mat-checkbox-1'
    try:
        apply_to_future_periods_checkbox = browser.find_elements_by_id(apply_to_future_periods_checkbox_id)
        if len(apply_to_future_periods_checkbox):
            apply_to_future_periods_checkbox[0].click()
        else:
            pass
    except NoSuchElementException:
        print("Could not find apply to future periods checkbox")
        pass

    # This element has an id but it doesn't seem to work using find_elements_by_id, so using xpath instead
    finalize_changes_button_xpath = '//*[@id="mat-dialog-0"]/app-league-team-roster-confirm-dialog/mat-dialog-actions/div/button[2]/span'
    try:
        finalize_changes_button = browser.find_elements_by_xpath(finalize_changes_button_xpath)
        if len(finalize_changes_button):
            finalize_changes_button[0].click()
        else:
            pass
    except NoSuchElementException:
        print("Could not find finalize changes button")
        pass
def set_lineup(browser, team_roster_filepath):

    download_team_roster(browser, team_roster_filepath)
    df_skaters, df_goalies = import_team_roster_from_csv(team_roster_filepath)
    skater_move_list = create_move_list(df_skaters)
    goalie_move_list = create_move_list(df_goalies)
    xpath_move_list = convert_move_list_to_xpath(skater_move_list, goalie_move_list)
    if len(xpath_move_list):
        execute_move_list(browser, xpath_move_list)
    else:
        print("There are no moves to execute")
    browser.quit()

## MAIN FUNCTION ##

# Starts a timer to determine run time
start_time = time.time()

home_directory = os.getcwd() + '/'
login_credentials_filepath = home_directory + 'login_credentials.txt'
team_roster_filepath = home_directory + 'Fantrax-Team-Roster-Just the Beauties HockeyLeague.csv'
url_team_page = 'https://www.fantrax.com/fantasy/league/qyfm7iiajx6nt5tq/team/roster'


browser = browser_setup(home_directory)
login(browser, login_credentials_filepath)
# navigate_to_team_page(browser, url_team_page, 0)


set_lineup(browser, team_roster_filepath)
time.sleep(5)
# Calculates overall run time
end_time = time.time()
print("Runtime: {} seconds".format(round(end_time - start_time), 3))
