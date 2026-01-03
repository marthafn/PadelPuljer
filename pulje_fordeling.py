import numpy as np
import pandas as pd
# %matplotlib widget
from collections import defaultdict

pulje_størrelse = 7
min_pulje_størrelse = 5
max_teams_per_club = 2

hold_df = pd.read_csv("hold.csv")
klubber_df = pd.read_csv("klubber.csv")
køretider_df = pd.read_csv("køretider.csv")

herrehold = hold_df[hold_df["Liga"]=="DPF Ligaen"]

regioner = herrehold["Region"].unique()
divisioner = herrehold["Division"].unique()

række_df = herrehold[(herrehold["Region"]==regioner[0]) & (herrehold["Division"]==divisioner[2])]

hold_til_klub = række_df.set_index("Team id")["Hjemmebane"].to_dict()

def beregn_alle_køretider_i_række(række_df):
    """Beregner alle køretider i række"""
    alle_køretider_i_række = række_df[["Team id","Hjemmebane"]].merge(række_df[["Team id","Hjemmebane"]], how='cross')
    alle_køretider_i_række = alle_køretider_i_række.merge(køretider_df, left_on=["Hjemmebane_x", "Hjemmebane_y"], right_on=["Hjemmebane", "Udebane"], how='left', suffixes=('_left', '_right'))
    alle_køretider_i_række = alle_køretider_i_række.drop(columns=["Hjemmebane_x", "Hjemmebane_y"])
    alle_køretider_i_række = alle_køretider_i_række.rename(columns={"Team id_x": "Team id hjemmebane", "Team id_y": "Team id udebane"})
    alle_køretider_i_række = alle_køretider_i_række.drop_duplicates(subset=["Team id hjemmebane", "Team id udebane"])
        

    """ Opretter dict med alle køretider mellem klubber"""
    distance = defaultdict(int)

    for _, row in alle_køretider_i_række.iterrows():
        i = row["Team id hjemmebane"]
        j = row["Team id udebane"]
        distance[(i, j)] += row["Køretid"]
        distance[(j, i)] += row["Køretid"]
    
    return alle_køretider_i_række, distance


alle_køretider_i_række, distance = beregn_alle_køretider_i_række(række_df)

def saml_små_puljer(puljer):
    """ En række restpuljer kan opstå for de sidste puljer i den grådige algoritme
    Disse småpuljer samles i første omgang til puljer af præcis 7 hold og herefter en evt. rest.
    En evt rest fordeles i funktionen fordel_små_puljer()"""
    gyldige_puljer = []
    restpulje = []

    # Separate valid puljer and collect leftovers
    for pulje in puljer:
        if len(pulje) < pulje_størrelse:
            restpulje.extend(pulje)
        else:
            gyldige_puljer.append(pulje)

    # Split restpulje into chunks of size pulje_størrelse
    for i in range(0, len(restpulje), pulje_størrelse):
        gyldige_puljer.append(restpulje[i:i + pulje_størrelse])

    return gyldige_puljer

def håndhæv_max_to_klubber(puljer):
    """ Tjekker om nogen puljer indeholder mere end 2 hold fra samme klub
    I så fald foretages et tilfældigt bytte med et hold fra en anden pulje
    Byttet foretages under hensyn til ikke hermed at overstige max kravet"""
    for pulje in puljer:
        klubber_i_pulje = np.array([hold_til_klub[h] for h in pulje])
        vals, counts = np.unique(klubber_i_pulje, return_counts=True)
        overrepræsenterede_klubber = vals[counts > max_teams_per_club]
        overrepræsenterede_hold = [h for h in pulje if hold_til_klub[h] in overrepræsenterede_klubber]
        if overrepræsenterede_hold:
            for hold_ind in overrepræsenterede_hold[:]:

                for _, pulje_at_swappe in enumerate(puljer):
                    if pulje_at_swappe == pulje:
                        continue
                    klubber_i_swap = [hold_til_klub[h] for h in pulje_at_swappe]
                    if klubber_i_swap.count(hold_til_klub[hold_ind]) >= 2:
                        continue
                    hold_ud = pulje_at_swappe[0]
                    
                    pulje_at_swappe.remove(hold_ud)
                    pulje.remove(hold_ind)
                    
                    pulje.append(hold_ud)
                    pulje_at_swappe.append(hold_ind)

                    break 
    return puljer


def fordel_små_puljer(puljer):
    """Hvis antal_hold \\ antal_hold_pr_pulje ikke går op med heltalsdivision fordeles de tiloversblevne hold
    Hvis der er en rest på mindre end min_pulje_størrelse fordeles de resterende hold, således at puljer
    med pulje_størrelse + 1 dannes."""
    for pulje in puljer:
        if len(pulje) < min_pulje_størrelse:
            for hold_ind in pulje[:]:
                for _, pulje_at_swappe in enumerate(puljer):
                    if pulje_at_swappe == pulje:
                        continue
                    
                    pulje.remove(hold_ind)
                    pulje_at_swappe.append(hold_ind)

                    break 
            puljer.remove(pulje)
    return puljer
            

def grådig_fordeling(række_df):    
    """ Danner første bud på puljer gennem en grådig fordelingsalgoritme
    Gennemgår hold og vælger grådigt de 6 nærmeste hold, der ikke er fra samme klub
    
    For de sidst fordelte puljer vil der sjældent være 6 hold fra andre klubber tilbage.
    Her brydes puljerne op i puljer med mindre end 7 hold i hver pulje.
    Disse samles, hvorefter eventuelle overtrædelser af max_to_hold_fra_samme_klub-reglen håndteres ved tilfældige byt
    
    """ 
    hold_liste = række_df["Team id"].tolist()
    unused_teams = set(hold_liste)
    puljer_grådig = []

    while unused_teams:
        team = unused_teams.pop() 
        klub = hold_til_klub[team]

        possible_neighbors = alle_køretider_i_række[(alle_køretider_i_række["Team id hjemmebane"]==team) & \
                                (alle_køretider_i_række["Team id udebane"].isin(unused_teams)) & \
                                (alle_køretider_i_række["Udebane"] != klub)]

        possible_neighbors = possible_neighbors.drop_duplicates(subset="Udebane",keep="first")
        nearest_neighbors = possible_neighbors.sort_values(by="Køretid").head(pulje_størrelse - 1)
        nearest_neighbors = nearest_neighbors["Team id udebane"].tolist()
        pulje = [team] + nearest_neighbors
        puljer_grådig.append(pulje)
        
        for team in nearest_neighbors:
            unused_teams.remove(team)
            
    puljer_grådig = saml_små_puljer(puljer_grådig)
    puljer_grådig = håndhæv_max_to_klubber(puljer_grådig)
    puljer_grådig = fordel_små_puljer(puljer_grådig)
    puljer_grådig = håndhæv_max_to_klubber(puljer_grådig)
    
    
    return puljer_grådig

def pulje_cost(pulje):
    """ Beregner den samlede køretid for en pulje"""
    return sum(distance[(i, j)] for idx, i in enumerate(pulje) for j in pulje[idx + 1:])

def swap_delta(pulje_a, pulje_b, i, j):
    """ Beregner gevinst bed at flytte i fra pulje a til pulje b
    og j fra pulje b til pulje a (direkte byt)"""
    
    delta = 0

    for x in pulje_a:
        if x != i:
            delta -= distance[(i, x)]
            delta += distance[(j, x)]

    for x in pulje_b:
        if x != j:
            delta -= distance[(j, x)]
            delta += distance[(i, x)]

    return delta

def avg_team_distance(team, pulje, distance):
    """ Beregner gennemsnitlig køretid for et givent hold i en pulje"""
    return sum(distance[(team, t)] for t in pulje if t != team) / (len(pulje) - 1)

def is_outlier(team, pulje, distance, outlier_factor):
    """ Tester om et hold er en outlier i sin pulje (dvs. om holdets gennemsnitlige køretid
    overstiger den gennemsnitlige køretid for de andre hold med en faktor outlier_factor)"""
    team_avg = avg_team_distance(team, pulje, distance)
    others = [avg_team_distance(t, pulje, distance) for t in pulje if t != team]
    return team_avg > outlier_factor * (sum(others) / len(others))

def club_count_ok(pulje, hold_til_klub):
    """ Tjekker om antal hold fra samme klub overstiger 1"""
    counts = {}
    for t in pulje:
        c = hold_til_klub[t]
        counts[c] = counts.get(c, 0) + 1
        if counts[c] > max_teams_per_club:
            return False
    return True

def club_constraint_ok(old_a, old_b,new_a, new_b,i, j,distance,hold_til_klub, outlier_factor):
    """ Tjekker om en ny puljefordeling er tilladt.
    Tjekker om antallet af hold fra samme klub i den nye fordeling er tilladt udfra reglerne:
    1) Et hold fra samme klub er altid tilladt
    2) Tre eller flere hold fra samme klub er aldrig tilladt
    3) To hold fra samme klub tilladt hvis det medfører en betydelig formindskning af holdenes køretid
    """
    # Hard cap: never more than 2 per club
    if not (club_count_ok(new_a, hold_til_klub) and
            club_count_ok(new_b, hold_til_klub)):
        return False

    # If no duplicate clubs, always OK
    if len({hold_til_klub[t] for t in new_a}) == len(new_a) and \
       len({hold_til_klub[t] for t in new_b}) == len(new_b):
        return True

    # Otherwise: allow only if i or j is a travel outlier
    if is_outlier(i, old_a, distance, outlier_factor):
        return True
    if is_outlier(j, old_b, distance, outlier_factor):
        return True

    return False

def improvement_fordeling_soft_cap(puljer,outlier_factor):
    """ Givet en grådig fordeling afsøges 2-opt forbedringsmuligheder
    et byt sker hvis:
    puljens samlede køretid mindskes ved byttet 
    OG
    (det indgående hold kommer fra en klub der ikke allerede er i puljen
    ELLER
    det indgående hold kommer fra en klub der har præcist ét hold fra i puljen, men det udgående hold er en outlier i puljen)
    
    en outlier er defineret som et hold hvis gennemsnitlige rejsetid er mere ind outlier_factor større end resten af puljens gennemsnit
    """
    puljer_improvement_soft_cap = [p.copy() for p in puljer]

    pulje_costs = [pulje_cost(p) for p in puljer_improvement_soft_cap]

    improved = True
    while improved:
        improved = False
        for a in range(len(puljer_improvement_soft_cap)):
            for b in range(a + 1, len(puljer_improvement_soft_cap)):
                for i in puljer_improvement_soft_cap[a]:
                    for j in puljer_improvement_soft_cap[b]:

                        new_a = puljer_improvement_soft_cap[a].copy()
                        new_b = puljer_improvement_soft_cap[b].copy()

                        new_a.remove(i)
                        new_b.remove(j)
                        new_a.append(j)
                        new_b.append(i)

                        if not club_constraint_ok(puljer_improvement_soft_cap[a], puljer_improvement_soft_cap[b], new_a, new_b, i, j, distance, hold_til_klub, outlier_factor = outlier_factor):
                            continue

                        delta = swap_delta(puljer_improvement_soft_cap[a], puljer_improvement_soft_cap[b], i, j)

                        if delta < 0:
                            puljer_improvement_soft_cap[a] = new_a
                            puljer_improvement_soft_cap[b] = new_b
                            pulje_costs[a] += delta
                            pulje_costs[b] += delta
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
    return puljer_improvement_soft_cap


def puljefordeling(række_df, outlier_factor):
    puljer_grådig = grådig_fordeling(række_df)
    puljer_improvement = improvement_fordeling_soft_cap(puljer_grådig,outlier_factor)
    
    return puljer_improvement











# hold_til_klub = None

# def setup_hold_til_klub(df):
#     global hold_til_klub
#     hold_til_klub = df.set_index("Team id")["Hjemmebane"].to_dict()


# def beregn_alle_køretider_i_række(række_df,køretider):
#     """Beregner alle køretider i række"""
#     alle_køretider_i_række = række_df[["Team id","Hjemmebane"]].merge(række_df[["Team id","Hjemmebane"]], how='cross')
#     alle_køretider_i_række = alle_køretider_i_række.merge(køretider, left_on=["Hjemmebane_x", "Hjemmebane_y"], right_on=["Hjemmebane", "Udebane"], how='left', suffixes=('_left', '_right'))
#     alle_køretider_i_række = alle_køretider_i_række.drop(columns=["Hjemmebane_x", "Hjemmebane_y"])
#     alle_køretider_i_række = alle_køretider_i_række.rename(columns={"Team id_x": "Team id hjemmebane", "Team id_y": "Team id udebane"})
#     alle_køretider_i_række = alle_køretider_i_række.drop_duplicates(subset=["Team id hjemmebane", "Team id udebane"])
        
#     distance = defaultdict(int)

#     for _, row in alle_køretider_i_række.iterrows():
#         i = row["Team id hjemmebane"]
#         j = row["Team id udebane"]
#         distance[(i, j)] += row["Køretid"]
#         distance[(j, i)] += row["Køretid"]
    
#     return alle_køretider_i_række, distance

# def saml_små_puljer(puljer):
#     """ En række restpuljer kan opstå for de sidste puljer i den grådige algoritme
#     Disse småpuljer samles i første omgang til puljer af præcis 7 hold og herefter en evt. rest.
#     En evt rest fordeles i funktionen fordel_små_puljer()"""
#     gyldige_puljer = []
#     restpulje = []

#     # Separate valid puljer and collect leftovers
#     for pulje in puljer:
#         if len(pulje) < pulje_størrelse:
#             restpulje.extend(pulje)
#         else:
#             gyldige_puljer.append(pulje)

#     # Split restpulje into chunks of size pulje_størrelse
#     for i in range(0, len(restpulje), pulje_størrelse):
#         gyldige_puljer.append(restpulje[i:i + pulje_størrelse])

#     return gyldige_puljer

# def håndhæv_max_to_klubber(puljer):
#     """ Tjekker om nogen puljer indeholder mere end 2 hold fra samme klub
#     I så fald foretages et tilfældigt bytte med et hold fra en anden pulje
#     Byttet foretages under hensyn til ikke hermed at overstige max kravet"""
#     for pulje in puljer:
#         klubber_i_pulje = np.array([hold_til_klub[h] for h in pulje])
#         vals, counts = np.unique(klubber_i_pulje, return_counts=True)
#         overrepræsenterede_klubber = vals[counts > max_teams_per_club]
#         overrepræsenterede_hold = [h for h in pulje if hold_til_klub[h] in overrepræsenterede_klubber]
#         if overrepræsenterede_hold:
#             for hold_ind in overrepræsenterede_hold[:]:

#                 for _, pulje_at_swappe in enumerate(puljer):
#                     if pulje_at_swappe == pulje:
#                         continue
#                     klubber_i_swap = [hold_til_klub[h] for h in pulje_at_swappe]
#                     if klubber_i_swap.count(hold_til_klub[hold_ind]) >= 2:
#                         continue
#                     hold_ud = pulje_at_swappe[0]
                    
#                     pulje_at_swappe.remove(hold_ud)
#                     pulje.remove(hold_ind)
                    
#                     pulje.append(hold_ud)
#                     pulje_at_swappe.append(hold_ind)

#                     break 
#     return puljer


# def fordel_små_puljer(puljer):
#     """Hvis antal_hold \\ antal_hold_pr_pulje ikke går op med heltalsdivision fordeles de tiloversblevne hold
#     Hvis der er en rest på mindre end min_pulje_størrelse fordeles de resterende hold, således at puljer
#     med pulje_størrelse + 1 dannes."""
#     for pulje in puljer:
#         if len(pulje) < min_pulje_størrelse:
#             for hold_ind in pulje[:]:
#                 for _, pulje_at_swappe in enumerate(puljer):
#                     if pulje_at_swappe == pulje:
#                         continue
                    
#                     pulje.remove(hold_ind)
#                     pulje_at_swappe.append(hold_ind)

#                     break 
#             puljer.remove(pulje)
#     return puljer
            


# def grådig_fordeling(række_df,alle_køretider_i_række):    
#     """ Danner første bud på puljer gennem en grådig fordelingsalgoritme
#     Gennemgår hold og vælger grådigt de 6 nærmeste hold, der ikke er fra samme klub
    
#     For de sidst fordelte puljer vil der sjældent være 6 hold fra andre klubber tilbage.
#     Her brydes puljerne op i puljer med mindre end 7 hold i hver pulje.
#     Disse samles, hvorefter eventuelle overtrædelser af max_to_hold_fra_samme_klub-reglen håndteres ved tilfældige byt
    
#     """ 
#     hold_liste = række_df["Team id"].tolist()
#     unused_teams = set(hold_liste)
#     puljer_grådig = []

#     while unused_teams:
#         team = unused_teams.pop() 
#         klub = hold_til_klub[team]

#         possible_neighbors = alle_køretider_i_række[(alle_køretider_i_række["Team id hjemmebane"]==team) & \
#                                 (alle_køretider_i_række["Team id udebane"].isin(unused_teams)) & \
#                                 (alle_køretider_i_række["Udebane"] != klub)]

#         possible_neighbors = possible_neighbors.drop_duplicates(subset="Udebane",keep="first")
#         nearest_neighbors = possible_neighbors.sort_values(by="Køretid").head(pulje_størrelse - 1)
#         nearest_neighbors = nearest_neighbors["Team id udebane"].tolist()
#         pulje = [team] + nearest_neighbors
#         puljer_grådig.append(pulje)
        
#         for team in nearest_neighbors:
#             unused_teams.remove(team)
            
#     puljer_grådig = saml_små_puljer(puljer_grådig)
#     puljer_grådig = håndhæv_max_to_klubber(puljer_grådig)
#     puljer_grådig = fordel_små_puljer(puljer_grådig)
#     puljer_grådig = håndhæv_max_to_klubber(puljer_grådig)
    
    
#     return puljer_grådig


# def pulje_cost(pulje,distance):
#     """ Beregner den samlede køretid for en pulje"""
#     return sum(distance[(i, j)] for idx, i in enumerate(pulje) for j in pulje[idx + 1:])

# def swap_delta(pulje_a, pulje_b, i, j,distance):
#     """ Beregner gevinst bed at flytte i fra pulje a til pulje b
#     og j fra pulje b til pulje a (direkte byt)"""
    
#     delta = 0

#     for x in pulje_a:
#         if x != i:
#             delta -= distance[(i, x)]
#             delta += distance[(j, x)]

#     for x in pulje_b:
#         if x != j:
#             delta -= distance[(j, x)]
#             delta += distance[(i, x)]

#     return delta

# def avg_team_distance(team, pulje, distance):
#     """ Beregner gennemsnitlig køretid for et givent hold i en pulje"""
#     return sum(distance[(team, t)] for t in pulje if t != team) / (len(pulje) - 1)

# def is_outlier(team, pulje, distance, outlier_factor):
#     """ Tester om et hold er en outlier i sin pulje (dvs. om holdets gennemsnitlige køretid
#     overstiger den gennemsnitlige køretid for de andre hold med en faktor outlier_factor)"""
#     team_avg = avg_team_distance(team, pulje, distance)
#     others = [avg_team_distance(t, pulje, distance) for t in pulje if t != team]
#     return team_avg > outlier_factor * (sum(others) / len(others))

# def club_count_ok(pulje,hold_til_klub):
#     """ Tjekker om antal hold fra samme klub overstiger 1"""
#     counts = {}
#     for t in pulje:
#         c = hold_til_klub[t]
#         counts[c] = counts.get(c, 0) + 1
#         if counts[c] > max_teams_per_club:
#             return False
#     return True

# def club_constraint_ok(old_a, old_b,new_a, new_b,i, j,distance, outlier_factor,række_df):
#     """ Tjekker om en ny puljefordeling er tilladt.
#     Tjekker om antallet af hold fra samme klub i den nye fordeling er tilladt udfra reglerne:
#     1) Et hold fra samme klub er altid tilladt
#     2) Tre eller flere hold fra samme klub er aldrig tilladt
#     3) To hold fra samme klub tilladt hvis det medfører en betydelig formindskning af holdenes køretid
#     """
#     # Hard cap: never more than 2 per club
#     if not (club_count_ok(new_a,række_df) and
#             club_count_ok(new_b,række_df)):
#         return False

#     # If no duplicate clubs, always OK
#     if len({hold_til_klub[t] for t in new_a}) == len(new_a) and \
#        len({hold_til_klub[t] for t in new_b}) == len(new_b):
#         return True

#     # Otherwise: allow only if i or j is a travel outlier
#     if is_outlier(i, old_a, distance, outlier_factor):
#         return True
#     if is_outlier(j, old_b, distance, outlier_factor):
#         return True

#     return False

# def improvement_fordeling_soft_cap(puljer,distance,række_df,outlier_factor):
#     """ Givet en grådig fordeling afsøges 2-opt forbedringsmuligheder
#     et byt sker hvis:
#     puljens samlede køretid mindskes ved byttet 
#     OG
#     (det indgående hold kommer fra en klub der ikke allerede er i puljen
#     ELLER
#     det indgående hold kommer fra en klub der har præcist ét hold fra i puljen, men det udgående hold er en outlier i puljen)
    
#     en outlier er defineret som et hold hvis gennemsnitlige rejsetid er mere ind outlier_factor større end resten af puljens gennemsnit
#     """
#     puljer_improvement_soft_cap = [p.copy() for p in puljer]

#     pulje_costs = [pulje_cost(p,distance) for p in puljer_improvement_soft_cap]

#     improved = True
#     while improved:
#         improved = False
#         for a in range(len(puljer_improvement_soft_cap)):
#             for b in range(a + 1, len(puljer_improvement_soft_cap)):
#                 for i in puljer_improvement_soft_cap[a]:
#                     for j in puljer_improvement_soft_cap[b]:

#                         new_a = puljer_improvement_soft_cap[a].copy()
#                         new_b = puljer_improvement_soft_cap[b].copy()

#                         new_a.remove(i)
#                         new_b.remove(j)
#                         new_a.append(j)
#                         new_b.append(i)

#                         if not club_constraint_ok(puljer_improvement_soft_cap[a], puljer_improvement_soft_cap[b], new_a, new_b, i, j, distance, outlier_factor, række_df):
#                             continue

#                         delta = swap_delta(puljer_improvement_soft_cap[a], puljer_improvement_soft_cap[b], i, j,distance)

#                         if delta < 0:
#                             puljer_improvement_soft_cap[a] = new_a
#                             puljer_improvement_soft_cap[b] = new_b
#                             pulje_costs[a] += delta
#                             pulje_costs[b] += delta
#                             improved = True
#                             break
#                     if improved:
#                         break
#                 if improved:
#                     break
#     return puljer_improvement_soft_cap