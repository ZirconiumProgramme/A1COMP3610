import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px

#Functions That Construct Graphs Using DUCKDB SQL queries where necessary
def constructBar(df):
    con = duckdb.connect(':memory:')
    con.register("df", df)

    result = con.execute('''
        SELECT 
            PU_Zone,
            COUNT(*) as Number_Of_Trips
        FROM df
        GROUP BY PU_Zone
        ORDER BY Number_Of_Trips DESC
        LIMIT 10
    ''').df()

    fig = px.bar(
        result,
        x='PU_Zone',
        y='Number_Of_Trips',
        hover_data=['PU_Zone', 'Number_Of_Trips'],
        title='Number of Trips vs PU_Zone',
        opacity=.6
    )
    return fig

def constructLine(df):
    con = duckdb.connect(':memory:')
    con.register("df", df)

    result = con.execute(''' 
        SELECT
            HOUR(tpep_dropoff_datetime) as hour, 
            AVG(fare_amount) as avg_fare
        FROM df
        GROUP BY hour
        ORDER BY hour
    ''').df()

    fig = px.line(
        result,
        x='hour',
        y='avg_fare',
        hover_data=['hour', 'avg_fare'],
        title='Chart Showing Average Fare($) by Hour of the Day',
    )
    return fig

def constructHist(df):
    max_distance = df["trip_distance"].quantile(0.99)

    fig = px.histogram(
        df[df["trip_distance"] <= max_distance],
        x = 'trip_distance',
        hover_data = ['trip_distance'],
        nbins = 285,
        title = 'Distribution of Trip Distances in Miles',
    )
    return fig

def constructPie(df):
    result = df['payment_label'].value_counts().reset_index()
    result.columns = ['payment_label', 'count']

    fig = px.pie(
        result,
        values='count',
        names='payment_label',
        title='Breakdown of Payment Types',
    )
    return fig

def constructHeat(df):
    con = duckdb.connect(':memory:')
    con.register("df", df)

    result = con.execute('''
        SELECT 
            DAYNAME(tpep_pickup_datetime) as day_of_week,
            HOUR(tpep_pickup_datetime) as hour,
            COUNT(*) as trip_count
        FROM df
        GROUP BY day_of_week, hour
        ORDER BY hour
    ''').df()

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                 'Friday', 'Saturday', 'Sunday']

    fig = px.density_heatmap(
        result,
        x='hour',
        y='day_of_week',
        z='trip_count',
        category_orders={'day_of_week': day_order},
        title='Weekly Trip Patterns (Day vs. Hour)',
    )
    return fig


#Filter Functions
def filterDate(df, start, end):
    df = df[
        (df['tpep_pickup_datetime'].dt.date >= start) & 
        (df['tpep_pickup_datetime'].dt.date <= end) 
    ]
    return df


def filterHour(df, range):
    df = df[
    (df['pickup_hour'] >= range[0]) & 
    (df['pickup_hour'] <= range[1]) 
    ]
    return df

def filterPaymentType(df, selection):
    df = df[df['payment_label'].isin(selection)]
    return df

#Start of DashBoard Creation
st.set_page_config(
    page_title='NYC Taxi Dashboard',
    page_icon='🚕',
    layout='wide',
    initial_sidebar_state='expanded'
)

#Reading in the cleaned parquet into dataframe
df = pd.read_parquet('Transformed_TripData.parquet')
#Renaming a column to save some time typing
df['pickup_hour'] = df['tpep_pickup_datetime'].dt.hour


st.title('Dashboard Showing Trip Data for Janurary 2024 🚕')
st.markdown("""
    This Dashboard Provides Key Insights into the Trends of NYC Taxi Passengers and Drivers for the Janurary 2024 period 
    using clear vizulizations and interractive filters.
"""
)



#Displaying Key Insights

#Puts total revenue in millions to aid in readability
sum = df["total_amount"].sum()
sum = sum / 1000000
sum = round(sum, 2)

#Rest of Insights
st.subheader("Key Insights🔑")
with st.container(border=True):
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric('Total Trips', f'{round((len(df)/1000000), 2)} M' )
    col2.metric('Avg Fare', f'${df["fare_amount"].mean():.2f}')
    col3.metric('Total Revenue', f' ${sum} M')
    col4.metric('Avg Distance', f'{df["trip_distance"].mean():.2f} mi')
    col5.metric('Avg Trip Duration', f'{df["trip_duration_minutes"].mean():.2f} min')


#DashBoard Filters
st.sidebar.header("Dashboard Filters 🛠️")


min_date = df['tpep_pickup_datetime'].min().date()
max_date = df['tpep_pickup_datetime'].max().date()

dstart, dend = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)


hrange = st.sidebar.slider(
    "Select Hour Range",
    0, 23, (0, 23)
)


payment_map = {1: 'Credit Card', 2: 'Cash', 3: 'No Charge', 4: 'Dispute'}
df['payment_label'] = df['payment_type'].map(payment_map).fillna('Unknown')
available_payments = df['payment_label'].unique().tolist()

selected_payments = st.sidebar.multiselect(
    "Select Payment Types",
    options=available_payments,
    default=available_payments
)
#Filtering
df = filterDate(df, dstart, dend)
df = filterHour(df, hrange)
df = filterPaymentType(df, selected_payments)


#Constructing Vizulization Portion + markdown for analysis of graphs
st.subheader("Visualizations 📈")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Top 10 P/U Zones", "Average Fare by Hour of Day", 
                                        "Distribution of Distances", "Breakdown of Payment Types",
                                         "Trips by Day of Week and Hour" ])

with tab1:
    fig_1 = constructBar(df)
    st.plotly_chart(fig_1, use_container_width=True)
    st.subheader("Insights")
    st.markdown("This showcases the 10 busiest pickup locations. These pickup locations make up 31 Percent all of the trips in the data set. " \
    "Based on this small snapshot a very small decline be seen between each of the values with the sharpest decline coming 4th and 5th ranked pick up locations" \
    "Meaning that atleast within the top 10 there is a relatively even distribution of pick up locations")

with tab2:
   fig_2 = constructLine(df)
   st.plotly_chart(fig_2, use_container_width=True)
   st.subheader("Insights")
   st.markdown("This line chart shows the Average Fare by hour. During the hours of 7 to 12 the fare is at it's lowest most likely cab drivers" \
   " dealing with the fact that most people are in work during these times. The fares gradually increase from hour 12 to hour 17 as people seek transport back" \
   "home. Dropping off until till 8 and reaching a new peak at 0 hour as people go to and from night time events/parties/ect. The highest peak comes during the monrning" \
   "hours as people commute from hom to work")

with tab3:
    fig_3 = constructHist(df)
    st.plotly_chart(fig_3, use_container_width=True)
    st.subheader("Insights")
    st.markdown("This histogram showcases the distribution of trip distance. In this graph there is a very big peak in the .75 mile to 1.15 mile range" \
    "Which can be explained by the NYC density. Genrally people take shorter trips within the city because of this")

with tab4:
    fig_4 = constructPie(df)
    st.plotly_chart(fig_4, use_container_width=True)
    st.subheader("Insights")
    st.markdown("This Pie Chart gives the breakdown on how trips are paid for. Credit Cards take up over 80 percent of the trips. Most likely due to the NYC being a very modern city" \
    "customers have many ways to pay using credit card wether it be through an app or NFC which is made available to them in these yellow taxi cabs")


with tab5:
    fig_5 = constructHeat(df)
    st.plotly_chart(fig_5, use_container_width=True)
    st.subheader("Insights")
    st.markdown("This a Heat Graph showing how many trips occur based on Day and Hour. Intrestingly enough this graph can be read as an inverse of the Average fare" \
    "This can be due to price gouging or just passengers taking longer trips during their commute. There are other obvious insights as well the Weekends are significantly less buys than" \
    "the weekdays and the early afternoon period makes up for a majority of trips regardless of day")


