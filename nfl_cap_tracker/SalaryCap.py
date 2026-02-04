import streamlit as st
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import StringIO
from bs4 import BeautifulSoup
import plotly.express as px

# Set Page Config
st.set_page_config(page_title="NFL Positional Cap Tracker", layout="wide")

st.title("🏈 NFL Positional Spending Tracker")
st.write("Data parsed from [Spotrac NFL Cap Tracker](https://www.spotrac.com/nfl/cap)")

def create_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Create a global session
session = create_session()

@st.cache_data(ttl=3600)
def get_nfl_data(year):
    url = f"https://www.spotrac.com/nfl/cap/{year}/"
    # Mimic a real browser to avoid 403 Forbidden
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # Increased timeout to 120s and use session with retries
    response = session.get(url, headers=headers, timeout=120)
    response.raise_for_status() # Raise an error for bad status codes

    soup = BeautifulSoup(response.content, 'html.parser')
    tables = pd.read_html(StringIO(str(soup)))
    
    # Typically, the first table contains the team-by-team summary
    df = tables[0]
    
    # Cleaning the columns (Spotrac often has nested headers)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(-1)
    
    # Rename 'Total Cap Allocations' to 'Total Cap' to match existing logic
    # Also handle 'Cap Space All' if needed, but 'Total Cap Allocations' seems to be the one we want for spending
    if 'Total Cap Allocations' in df.columns:
        df.rename(columns={'Total Cap Allocations': 'Total Cap'}, inplace=True)
    elif 'Total Cap Top-51' in df.columns:
         df.rename(columns={'Total Cap Top-51': 'Total Cap'}, inplace=True)

    # Clean Team Name (remove duplicates like "TEN TEN")
    # We split by space. If the first and last parts are identical (and length > 1), valid assumption it's a duplicate.
    def clean_team_name(name):
        if not isinstance(name, str): return name
        parts = name.split()
        # If duplicated exactly "TEN TEN" or "LV LV"
        if len(parts) == 2 and parts[0] == parts[1]:
            return parts[0]
        # For "New Orleans New Orleans" -> 4 parts. 
        # Heuristic: if string is exactly doubled with a space
        mid = len(name) // 2
        if name[:mid] == name[mid:].strip():
             return name[:mid].strip()
        # Fallback: Just return as is for now if not detected
        return name

    if 'Team' in df.columns:
        df['Team'] = df['Team'].apply(clean_team_name)

    return df

# Global mapping for Spotrac
TEAM_SLUGS = {
    'ARI': 'arizona-cardinals',
    'ATL': 'atlanta-falcons',
    'BAL': 'baltimore-ravens',
    'BUF': 'buffalo-bills',
    'CAR': 'carolina-panthers',
    'CHI': 'chicago-bears',
    'CIN': 'cincinnati-bengals',
    'CLE': 'cleveland-browns',
    'DAL': 'dallas-cowboys',
    'DEN': 'denver-broncos',
    'DET': 'detroit-lions',
    'GB': 'green-bay-packers',
    'HOU': 'houston-texans',
    'IND': 'indianapolis-colts',
    'JAX': 'jacksonville-jaguars',
    'KC': 'kansas-city-chiefs',
    'LAC': 'los-angeles-chargers',
    'LAR': 'los-angeles-rams',
    'LV': 'las-vegas-raiders',
    'MIA': 'miami-dolphins',
    'MIN': 'minnesota-vikings',
    'NE': 'new-england-patriots',
    'NO': 'new-orleans-saints',
    'NYG': 'new-york-giants',
    'NYJ': 'new-york-jets',
    'PHI': 'philadelphia-eagles',
    'PIT': 'pittsburgh-steelers',
    'SEA': 'seattle-seahawks',
    'SF': 'san-francisco-49ers',
    'TB': 'tampa-bay-buccaneers',
    'TEN': 'tennessee-titans',
    'WAS': 'washington-commanders'
}

@st.cache_data(ttl=3600)
def get_team_real_data(team_name, year):
    # Handle cases like "Totals" or "Averages" which appear in the data but aren't teams
    if team_name in TEAM_SLUGS:
        slug = TEAM_SLUGS[team_name]
    else:
        # Fallback: try naive slug if not in map, but likely won't work for abbreviations
        slug = team_name.lower().replace(' ', '-')

    url = f"https://www.spotrac.com/nfl/{slug}/cap/{year}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.google.com/',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Use session with retries and longer timeout
        response = session.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        tables = pd.read_html(StringIO(str(soup)))
        
        if not tables:
            return None
            
        # Table 0 is usually the Active Roster
        df = tables[0]
        
        # Ensure we have Cap Hit and Pos columns
        # Spotrac Pos column might be 'Pos' or embedded
        # Cap Hit usually 'Cap Hit'
        
        if 'Pos' not in df.columns or 'Cap Hit' not in df.columns:
            return None
            
        # Clean currency
        df['Cap Hit'] = df['Cap Hit'].apply(clean_currency)
        
        # Group by Position
        pos_group = df.groupby('Pos')['Cap Hit'].sum().reset_index()
        pos_group.rename(columns={'Cap Hit': 'Estimated Spend', 'Pos': 'Position'}, inplace=True)
        
        # Calculate Percentages
        total_spending = pos_group['Estimated Spend'].sum()
        if total_spending > 0:
            pos_group['Percent of Cap'] = (pos_group['Estimated Spend'] / total_spending * 100).map('{:.1f}%'.format)
        else:
             pos_group['Percent of Cap'] = "0.0%"
             
        # Sort by spend
        pos_group = pos_group.sort_values(by='Estimated Spend', ascending=False)
        
        return pos_group

    except Exception as e:
        print(f"Error fetching team data: {e}")
        return None

def clean_currency(value):
    if isinstance(value, str):
        return float(value.replace('$', '').replace(',', ''))
    return value

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def get_league_data(year):
    # This will take time, so we should check if we can parallelize or just notify user
    all_team_data = []
    
    # Progress bar handled in UI normally, but inside cache we can't easily update UI.
    # We will just loop here.
    
    total_spend_by_pos = {}
    
    # Iterate through all teams in our slug map
    # Sort keys to ensure deterministic order for caching
    teams = sorted(TEAM_SLUGS.keys())
    
    for team_abbr in teams:
        # This calls the cached function, so if they visited the team page before, it's instant
        df = get_team_real_data(team_abbr, year)
        
        if df is not None and not df.empty:
            # df has columns: Position, Estimated Spend, Percent of Cap
            for index, row in df.iterrows():
                pos = row['Position']
                spend = row['Estimated Spend']
                
                if pos in total_spend_by_pos:
                    total_spend_by_pos[pos] += spend
                else:
                    total_spend_by_pos[pos] = spend
                    
    # Create League DF
    if not total_spend_by_pos:
        return None
        
    league_total = sum(total_spend_by_pos.values())
    
    league_df = pd.DataFrame(list(total_spend_by_pos.items()), columns=['Position', 'Average Spend'])
    
    # Calculate Average per Team (divide by 32)
    league_df['Average Spend'] = league_df['Average Spend'] / 32
    
    # Calculate Percentage of League Total
    league_df['Percentage'] = league_df['Average Spend'] / (league_total / 32)
    
    return league_df

# Sidebar for controls
year = st.sidebar.selectbox("Select Season", ["2024", "2025", "2026"])
view_type = st.sidebar.radio("View Mode", ["League Overview", "Team Specific Breakdown"])

try:
    df = get_nfl_data(year)
    
    # Display raw data option
    if st.checkbox("Show Raw Data Table"):
        st.dataframe(df)

    # Note: Spotrac's main page shows team totals. 
    # To get deep POSITIONAL data, we simulate the logic usually found in their positional breakdown tool.
    
    # Mock Positional logic based on current league averages for visualization
    # In a production app, you would iterate through each team URL found in df['Team']
    positions = {
        "QB": 0.12, "OL": 0.18, "WR": 0.11, "RB": 0.04, "TE": 0.04,
        "DL": 0.10, "EDGE": 0.12, "LB": 0.07, "CB": 0.09, "S": 0.06, "Spec": 0.03, "Dead": 0.04
    }

    if view_type == "League Overview":
        st.subheader("Average League Spending per Position")
        
        # Calculate totals based on the $255.4M (2024) or $279.2M (2025) cap
        total_cap = 279200000 
        
        # Default mock data (fast load)
        pos_df = pd.DataFrame({
            "Position": positions.keys(),
            "Percentage": positions.values(),
            "Average Spend": [v * total_cap for v in positions.values()]
        })
        
        # Option to load real data
        st.info("The charts below initially show estimated averages. Click to calculate real-time averages from all 32 teams.")
        
        if st.button("Calculate Real-Time League Averages"):
            with st.status("Fetching data for all 32 teams...", expanded=True) as status:
                # We need to manually iterate to show progress if not cached
                teams = sorted(TEAM_SLUGS.keys())
                progress_bar = st.progress(0)
                
                real_league_data = {}
                
                for i, team in enumerate(teams):
                    status.write(f"Fetching {team}...")
                    try:
                        get_team_real_data(team, year) # Prime the cache
                    except:
                        pass
                    progress_bar.progress((i + 1) / len(teams))
                
                status.update(label="Calculation Complete!", state="complete", expanded=False)
            
            # Now call the aggregator which will be fast since cache is primed
            real_df = get_league_data(year)
            if real_df is not None:
                pos_df = real_df
                st.success("Displaying Real-Time League Averages derived from Active Rosters.")

        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(pos_df, values='Percentage', names='Position', title="Cap Allocation %", hover_data=['Average Spend'])
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig)
            
        with col2:
            fig2 = px.bar(pos_df, x='Position', y='Average Spend', title="Average Dollars Spent")
            st.plotly_chart(fig2)
            
        csv = convert_df(pos_df)
        st.download_button(
            label="Download League Data as CSV",
            data=csv,
            file_name='league_cap_allocations.csv',
            mime='text/csv',
        )

    else:
        selected_team = st.selectbox("Select a Team", df['Team'].unique())
        team_data = df[df['Team'] == selected_team].iloc[0]
        
        st.metric(label=f"Total {selected_team} Cap", value=f"{team_data['Total Cap']}")
        
        # Try to fetch REAL data first
        with st.spinner(f"Fetching real-time roster data for {selected_team}..."):
            real_data = get_team_real_data(selected_team, year)
            
        if real_data is not None and not real_data.empty:
            st.success(f"Using real-time data for {selected_team}")
            team_pos_data = real_data
        else:
            st.warning("Could not fetch detailed roster. Showing ESTIMATED data based on league averages.")
            # Fallback to Mock Logic
            raw_cap = clean_currency(team_data['Total Cap'])
            team_pos_data = pd.DataFrame({"Position": positions.keys(), "Estimated Spend": [v * raw_cap for v in positions.values()]})

        col1, col2 = st.columns([1, 1])
        
        with col1:
            fig_team = px.pie(team_pos_data, values='Estimated Spend', names='Position', 
                             title=f"{selected_team} Cap Allocation",
                             hover_data=['Percent of Cap'])
            fig_team.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_team, use_container_width=True)
            
        with col2:
            # Reset index to hide the confusing row numbers from sorting
            st.table(team_pos_data.reset_index(drop=True))
        
        csv_team = convert_df(team_pos_data)
        st.download_button(
            label=f"Download {selected_team} Data as CSV",
            data=csv_team,
            file_name=f'{selected_team}_cap_allocations.csv',
            mime='text/csv',
        )

except Exception as e:
    st.error(f"Error fetching data: {e}")
    st.info("Spotrac may have changed their table structure. Please check the URL.")