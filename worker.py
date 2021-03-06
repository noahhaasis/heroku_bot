'''
Loads the timetable for the class 10a from the school website
and posts it to the class channel on discord.
'''
import asyncio
import datetime
import discord
import os
import re
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont


class Day:
    def __init__(self, date, entry_list):
        self.date = date
        # A row has the form [Stunde, Lehrer, Fach, Art, Vertreter, Fach, Raum]
        self.rows = entry_list

    def __str__(self):
        weekday_appended = False
        representation = ''
        column_names = [
            'Stunde', 'Lehrer', 'Fach', 'Art', 'Vertreter', 'Fach', 'Raum'
        ]
        column_shift = {
            'Stunde' : 7,
            'Lehrer' : 7,
            'Fach' : 5,
            'Art': 18,
            'Vertreter' : 10,
            'Fach' : 5,
            'Raum' : 6,
            'Wochentag': 11
        }
        representation += ''.join([' ' for _ in range(column_shift['Wochentag'])])
        for name in column_names:
            representation += '|'
            representation += name.ljust(column_shift[name])
        representation += '|'
        # Seperate the column names from the entries through a line of _'s
        representation += '\n'
        representation += ''.join(['_' for _ in range(sum(column_shift.values()) + len(column_shift) + 6)])
        representation += '\n'
        for row in self.rows:
            if not weekday_appended:
                representation += self.date.ljust(column_shift['Wochentag'])
                weekday_appended = True
            else:
                representation += ''.join([' ' for i in range(column_shift['Wochentag'])])
            representation += '|'
            for i, entry in enumerate(row):
                representation += entry.ljust(column_shift[column_names[i]])
                representation += '|'
            representation += '\n'
        return representation

def get_days_from_table(table):
    '''Takes a html table and returns a day object.'''
    res = []
    weekday = table[0]
    rows = [row for row in table[1].find_all('tr', class_=re.compile('(list odd|list even)'))]
    if not rows:
        return ''
    for row in rows:
        row_res = []
        columns = [column for column in row.find_all('td')]
        for i in range(1, 8):
            row_res.append(columns[i].text)
        res.append(row_res)
    return Day(weekday, res)

def get_table():
    # Request timetable
    base_url = 'https://www.wvsgym.de/vertretungsplans'
    iso_date = datetime.date.today().isocalendar()
    week_of_year = '{0:02d}'.format(iso_date[1] if iso_date[2] not in [6, 7] else iso_date[1] + 1)
    filename = 'w00022.htm' # NOTE: The filename if dependent on the class
    url = '/'.join([base_url, week_of_year, 'w', filename])
    username = 'schueler'
    password = os.environ['VERTRETUNGSPLAN_PASSWORD']
    response = requests.get(url, auth=(username, password))
    # TODO: Handle any failure

    # Write HTML to file
    with open('vertretungsplan.html', 'w') as f:
        f.write(response.text)

    # Parse the tabledata
    soup = BeautifulSoup(response.text, 'lxml')
    tables = soup.find_all('table', class_='subst')
    # convert the list to a list of two elements where the first is the weekday and the second the schedule
    weekdays = [
        'Montag',
        'Dienstag',
        'Mittwoch',
        'Donnerstag',
        'Freitag'
    ]
    for i in range(len(tables)):
        tables[i] = [weekdays[i], tables[i]]
    tables = [table for table in tables if not 'Keine Vertretungen' in table[1].text]
    days = [get_days_from_table(table) for table in tables]

    table = ''
    for day in days:
        table += str(day) + '\n'
    table = os.linesep.join([s for s in table.splitlines() if s])
    return table

client = discord.Client()

@client.event
async def on_ready():
    print('Ready')

@client.event
async def on_message(message):
    if message.author.bot:
        return
    elif '!plan text' in message.content:
        await client.send_message(message.channel, '```' + get_table() + '```')
    elif '!plan html' in message.content:
        pass
    elif '!plan' in message.content:
        # Create image from table and send it as reply
        plan_text = get_table()
        if plan_text and not plan_text.isspace()
            img = Image.new('RGB', (500, 10 + 20*len(plan_text.splitlines())), color = (255, 255, 255))
            d = ImageDraw.Draw(img)
            d.text((10,10), plan_text, fill=(0,0,0))
            img.save('plan.png')
            with open('plan.png', 'rb') as f:
                await client.send_file(message.channel, f)

client.run(os.environ['BOT'])
