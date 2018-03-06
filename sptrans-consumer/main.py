from sptrans.v0 import Client
import time
import psycopg2

client = Client()
client.authenticate('153bc35d149b8a337da0881349e2d297f149c3421c500c4ebcb038ae3e4b60d5')

"""
Route = {
    'code': 'CodigoLinha',
    'circular': 'Circular',
    'sign': 'Letreiro',
    'direction': 'Sentido',
    'type': 'Tipo',
    'main_to_sec': 'DenominacaoTPTS',
    'sec_to_main': 'DenominacaoTSTP',
    'info': 'Informacoes',
}
"""


def info_api():
    for route in client.search_routes('LAPA'):
        print(route)
        for stop in client.search_stops_by_route(route.code):
            print(stop)
        positions = client.get_positions(route.code)

        print(positions.time)
        for vehicle in positions.vehicles:
            print(vehicle)
        print


def info(code):
    for stop in client.search_stops_by_route(code):
        print(stop)
    t1 = positions = client.get_positions(code)

    print(positions.time)
    for vehicle in positions.vehicles:
        print(vehicle)

def get_vehicle(code):
    position = client.get_positions(code)
    return position.time, position.vehicles[0]

########################### DATABASE ###################################################################


class DataBase(object):

    def __init__(self):
        self.connect = psycopg2.connect("dbname=postgres user=postgres host=127.0.0.1 port=5432")
        self.cursor = self.connect.cursor()

    def desconect(self):
        self.cursor.close()
        self.connect.close()

    def execute(self, query, parametrs=None):
        if parametrs:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, parametrs)
        return self.cursor.fetchall()

    def commit(self):
        self.commit()

#############################     TRAJECTORIE VEHICLE #######################################

create_table_track = """
CREATE TABLE TRACK (
    id serial PRIMARY KEY,
    latitude NUMERIC,
    longitude NUMERIC,
    datetime timestamp,
    prefix integer
);
"""

insert_table_track = """
INSERT INTO TRACK ( latitude, longitude, prefix, datetime) VALUES (%s, %s, %s, %s)
"""

select_table_track_get = """
select * from TRACK
"""


class Track:

    def __init__(self, database):
        self.database = database

    def save(self, vehicle, datetime):
        self.database.execute(insert_table_track, (
            vehicle.latitude,
            vehicle.longitude,
            vehicle.prefix,
            str(datetime)
        ))
        self.database.commit()

    @classmethod
    def create_table(cls):
        return create_table_track

    def popule(self, data):
        self.latitude = data[1]
        self.longitude = data[2]
        self.prefix = data[3]
        self.datetime = data[4]


def main(code):
    while True:
        datetime, vehicle = get_vehicle(code)
        print(vehicle.prefix, vehicle.latitude, vehicle.longitude, datetime)
        time.sleep(15)


        # datetime, vehicle = get_vehicle(code)
        # print(vehicle)

#main(34041)

# db = DataBase()
# data = db.execute('select * from TRACK')
info_api()
# info(35050)
