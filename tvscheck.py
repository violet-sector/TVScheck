# tvscheck: program to scan some ingame stats from The Violet Sector
# Patrick Asselman 20200517
# python3.6+ needed to make sure dict order is preserved

from urllib import request, parse
from http import cookiejar
import copy, html, json, math, pickle, sys
import logindata    # username and password are stored in separate logindata.py file
from logindata import auth_header

urlbase = "https://www.violetsector.com/"

sectors = {
  1:    'Ajaxus Home',
  2:    'Boraxus',
  3:    'Planet Krilgore',
  4:    'Tibrar',
  5:    'Apollo Sector',
  6:    '81103',
  7:    'Red Sky City',
  8:    'Dreadlar',
  9:    'Southern Sector',
  10:   'Moons of Kaarp',
  11:   'Canopus West',
  12:   'The 3 Suns',
  13:   'Tripe',
  14:   'Orbital',
  15:   'Aquarious',
  16:   'Garen',
  17:   'Star City',
  18:   'Dragor',
  19:   'Durius Highlands',
  20:   'Perosis',
  21:   'Mattas Head',
  22:   'Acrador',
  23:   'The Tibran Mining Colony',
  24:   'C.T.6',
  25:   'The Asteroid Fields',
  26:   'New Sector Alpha',
  27:   'The Uncharted Sector',  
}

shiptypes = {
  1:  'P', #    Planet
  2:  'F', #    Goliath Mark II
  3:  'F', #    Flight Of Independence
  4:  'F', #    Fanged Fighter
  5:  'F', #    Golden Eagle
  6:  'F', #    Microw Fighter
  7:  'F', #    Demon Light Attacker
  8:  'F', #    Black Knight
  9:  'F', #    The Stinger
  10: 'F', #    Starship Fighter
  11: 'F', #    Sonic Speed Fighter
  12: 'C', #    Eagle Of Tunardia
  13: 'C', #    Shadow
  14: 'C', #    Cloud Of Death
  15: 'C', #    Mirage Mk III
  16: 'B', #    Galactic Bomber Alpha
  17: 'B', #    Hercules Bomber
  18: 'B', #    Blue Bird Bomber
  19: 'B', #    Boraxian Bomber
  20: 'B', #    Dark Speed Bomber
  21: 'B', #    Single Seated Tibran Bomber
  22: 'R', #    Repair Ship
  23: 'R', #    Repair Ship
  24: 'R', #    Repair Ship
  25: 'R', #    Repair Ship
  26: 'W', #    Carrier
  27: 'W', #    Carrier
  28: 'W', #    Carrier
  29: 'W', #    Carrier
  30: 'V', #    Cruiser
  31: 'V', #    Cruiser
  32: 'V', #    Cruiser
  33: 'V', #    Cruiser
  }
  
legions = {
  '1': 'J',
  '2': 'B',
  '3': 'K',
  '4': 'T',
  '5': 'R',  
}


def highlight(colour,str):   #print to screen with colour / background colour
  if colour == 'redbg':
    ret_str = '\x1b[7;31;80m' + str + '\x1b[0m'
  elif colour == 'greenbg':
    ret_str = '\x1b[6;30;42m' + str + '\x1b[0m'
  elif colour == 'red':
    ret_str = '\x1b[1;31;40m' + str + '\x1b[0m'
  elif colour == 'green':
    ret_str = '\x1b[1;32;40m' + str + '\x1b[0m'
  elif colour == 'blue':
    ret_str = '\x1b[1;34;40m' + str + '\x1b[0m'
  elif colour == 'yellow':
    ret_str = '\x1b[1;33;40m' + str + '\x1b[0m'
  return ret_str

def len_trunc(string, length):  #highlight-proof truncation of <string> to <length> chars
  if '\x1b[0m' in string:
    strip_hl = string[0:string.index('\x1b[0m')]
    if len(string) != len(strip_hl):
      string = strip_hl[0:length+10] + '\x1b[0m'
  else: 
    string = string[0:length]
  return string

def dictprint(dict, sizes):  #dict and sizes should both be dict with same keys
  returnstr = ''
  for key in dict:
    align = '^'
    addspace = 0
    if isinstance(sizes[key],str):
      align = sizes[key][-1]
      sizes[key] = int(sizes[key].strip(align))
    else:
      sizes[key] = sizes[key] + addspace
    if isinstance(dict[key], int):
      dict[key] = str(dict[key])
    if len(dict[key]) > sizes[key]:
      dict[key] = len_trunc(dict[key], sizes[key])
    extraspace = dict[key].count('\x1b[0m') * 14
    returnstr = returnstr + "{:{a}{width}.{width}s} ".format(dict[key],width=(sizes[key]+extraspace),a=align)
  returnstr = returnstr + '\n'   #newline at the end
  return returnstr

def real_len(string):
  reallength = len(string) - (string.count('\x1b[0m') * 14)
  return reallength
  
def print_side_by_side(string1, string2):
  str1list = string1.splitlines()
  str2list = string2.splitlines()
#  print(str1list)
#  print(str2list)
  maxlen1 = real_len(max(str1list, key=real_len))
  list1len = len(str1list)
  list2len = len(str2list)
  maxlistlen = max(list1len,list2len)
  if list1len > list2len:
    for i in range(list1len - list2len):
      str2list.append('')
  elif list2len > list1len:
    for i in range(list2len - list1len):
      str1list.append('')
  for i in range(maxlistlen):
    width = maxlen1 + (str1list[i].count('\x1b[0m') * 14)
    print("{:{w}.{w}s} {:s}".format(str1list[i], str2list[i], w = width))

def decode_sectors(navcomdict):
  for key in navcomdict:
    if not isinstance(navcomdict[key],str):
      navcomdict[key] = str(navcomdict[key])
    dom = ''
    for c in navcomdict[key]:
      dom = dom + legions[c]
    navcomdict[key] = dom
  for i in range(1,27):
    if not str(i) in navcomdict:
      navcomdict[str(i)] = 'N'
    if not str('27') in navcomdict:
      navcomdict['27'] = ' '
  return navcomdict

def print_map(planets):
  returnstr = ''
  width = {}
  for key in planets:
    width[key] = (5 + planets[key].count('\x1b[0m') * 14)
  returnstr = returnstr + "{:^{w1}.{w1}s}             {:^{w2}.{w2}s}\n".format(planets['27'], planets['17'], w1=width['27'], w2=width['17'])
  returnstr = returnstr + "\n                  {:^{w}.{w}s}\n".format(planets['1'], w=width['1'])
  returnstr = returnstr + "           {:^{w1}.{w1}s}         {:^{w2}.{w2}s}\n".format(planets['12'], planets['5'], w1=width['12'], w2=width['5'])
  returnstr = returnstr + "   {:^{w1}.{w1}s}                         {:^{w2}.{w2}s}\n".format(planets['24'], planets['18'], w1=width['24'], w2=width['18'])
  returnstr = returnstr + "        {:^{w1}.{w1}s}               {:^{w2}.{w2}s}\n".format(planets['16'], planets['13'], w1=width['16'], w2=width['13'])
  returnstr = returnstr + "\n       {:^{w1}.{w1}s}                  {:^{w2}.{w2}s}\n".format(planets['11'], planets['6'], w1=width['11'], w2=width['6'])
  returnstr = returnstr + "\n{:^{w1}.{w1}s} {:^{w2}.{w2}s}{:^{w3}.{w3}s} {:^{w4}.{w4}s} {:^{w5}.{w5}s}\n".format(planets['23'], planets['4'], planets['25'], planets['2'], planets['19'], w1=width['23'], w2=width['4'], w3=14+width['25'], w4=width['2'], w5=width['19'])
  returnstr = returnstr + "\n       {:^{w1}.{w1}s}                  {:^{w2}.{w2}s}\n".format(planets['10'], planets['7'], w1=width['10'], w2=width['7'])
  returnstr = returnstr + "\n        {:^{w1}.{w1}s}                {:^{w2}.{w2}s}\n".format(planets['15'], planets['14'], w1=width['15'], w2=width['14'])
  returnstr = returnstr + "   {:^{w1}.{w1}s}                         {:^{w2}.{w2}s}\n".format(planets['22'], planets['20'], w1=width['22'], w2=width['20'])
  returnstr = returnstr + "           {:^{w1}.{w1}s}         {:^{w2}.{w2}s}\n".format(planets['9'], planets['8'], w1=width['9'], w2=width['8'])
  returnstr = returnstr + "                  {:^{w}.{w}s}\n".format(planets['3'], w=width['3'])
  returnstr = returnstr + "\n                  {:^{w1}.{w1}s}                 {:^{w2}.{w2}s}\n".format(planets['21'], planets['26'], w1=width['21'], w2=width['26'])
  return returnstr

def getpage(url):
  if "login" in url:
    senddata = parse.urlencode({'username':logindata.username, 'password':logindata.password})
    senddata = senddata.encode('ascii')
  else:
    senddata = None
  request_obj = request.Request(urlbase + url, data = senddata, headers = auth_header)
  response = request.urlopen(request_obj)
  content_type = response.headers.get('content-type')
  contents = response.read()
  return content_type, contents.decode('utf-8')

def get_all_rankings():
  cont_type, rankings = getpage('json/rankings_pilots.php') # gets only first 100 
  if not cont_type == 'application/json':
    print("Error: Expected application/json output but instead got", cont_type)
    rankings = None
  return rankings

def un_html(line):
  line = line.strip()
  while '<' in line:
    code_start = line.find('<')
    code_end   = line.find('>')
    line = line.replace(line[code_start:code_end+1],'')
    line = html.unescape(line)
  return line

def process_pilots(all_rankings):
  for entry in all_rankings['rankings_pilots']:
    if entry['ship'] >= 26:
      entry['level'] = 6
    entry['legion'] = legions[str(entry['legion'])]  # change 12345 to JBKTR
    entry['ship'] = shiptypes[entry['ship']]
    entry.pop('maxhp')
    entry.pop('kills')
    entry.pop('deaths')
    entry.pop('online')
  return all_rankings['rankings_pilots']
      
### main ###

cj = cookiejar.CookieJar()
opener = request.build_opener(request.HTTPCookieProcessor(cj))
request.install_opener(opener)

# load previous state
old_data_available = False
try:
  with open ("tvscheck.dat",'rb') as f:
    old_lcname = pickle.load(f)
    old_vcname = pickle.load(f)
    old_health = pickle.load(f)
    old_HW_health = pickle.load(f)
    old_rankings = pickle.load(f)
    old_map = pickle.load(f)
    old_data_available = True
    old_pilotlist = []
    for item in range(len(old_rankings)):
      old_pilotlist.append(old_rankings[item]['tvs_username']) 
except:
  pass

resp_type, mainpage = getpage('login.php')
lc_controls = False
if "The game has been disabled." in mainpage:
  print("Error: Cannot login; Game disabled.")
  sys.exit(1)
for line in mainpage.splitlines():
  if "(LC)" in line:
    line = un_html(line)     #will have asterisk when active
    lcname = line.split("(LC)")[0]
    vcname = line.split("(LC)")[1].split("(VC)")
    vcname.pop()        # remove "100% approval rating" text
    lcname_backup = copy.copy(lcname)
    vcname_backup = copy.copy(vcname)
  elif "Homebase status" in line:
    HW_health = un_html(line).replace('Homebase status','')
    HW_health_backup = copy.copy(HW_health)
  elif "Legion control centre" in line:
    lc_controls = True
  elif "startTimer" in line:
    numbers = line.split('(')[1].split(')')[0].split(', ')
    ticksec = int(numbers[0])
    timesec = int(numbers[1])
    tick, timeleft = divmod(timesec, ticksec)
    tick += 1
    hrs, min = divmod((ticksec - timeleft), 3600)
    min = str(int(min/60))

cont_type, navcom = getpage('json/navcom_map.php')
if not cont_type == 'application/json':
  print("Error: Expected application/json output but instead got", cont_type)
  navcom = None
navcom_dict = json.loads(navcom)
pilotname = navcom_dict['player']['tvs_username']
health = str(navcom_dict['player']['hp'])
health_backup = copy.copy(health)

if old_data_available:
  if lcname != old_lcname:
    lcname = highlight('greenbg',lcname)
  if HW_health != old_HW_health:
    HW_health = highlight('redbg',str(HW_health))
  for name in vcname:
    try:
      if name !=  old_vcname[vcname.index(name)]:
        vcname[vcname.index(name)] = highlight('greenbg',name)
    except:
      pass
  if health != old_health:
    health = highlight('redbg',str(health))

print("Your pilot name:", pilotname, end=' ')
print("Tick: {} t-{}:{}".format(tick,hrs,min))
print("Your council:",lcname,vcname[0],vcname[1],vcname[2])
print("health:", health, end=' ')
print("HW health:", HW_health)
print('*************************************')

rankings_raw = get_all_rankings()
rankings_dict = json.loads(rankings_raw)
rankings = process_pilots(rankings_dict)
rankings_backup = copy.deepcopy(rankings)
rankings_formatted = ''
for pilot in rankings:
  printformat = {'tvs_username': '16<','legion':1,'level':1,'hp':'5>','ship':1,'score':'6>'}
  if old_data_available:
    deltadict = {}
    deltaprint = {}
    if not pilot['tvs_username'] in old_pilotlist:
      pilot['tvs_username'] = highlight('greenbg',pilot['tvs_username'])
    else:
      old_idx = old_pilotlist.index(pilot['tvs_username'])
      for key in pilot:
        if pilot[key] != old_rankings[old_idx][key]:
          if (key == 'hp') | (key == 'score'):
            deltanum = pilot[key] - old_rankings[old_idx][key]
            delta = "{:+d}".format(deltanum)
            deltadict['delta'+key] = delta
            deltaprint['delta'+key] = '5>'
          pilot[key] = highlight('greenbg',str(pilot[key]))
    pilot.update(deltadict)
    printformat.update(deltaprint)
  rankings_formatted = rankings_formatted + dictprint(pilot, printformat)

map = decode_sectors(navcom_dict['domination_info'])
map_backup = copy.deepcopy(map)
# map['1'] = 'K'   #test
for key in map:
  if old_data_available:
    try:
      if not map[key] == old_map[key]:
        hl_green = [] #highlight
        hl_red = []  
        for c in map[key]:
          if c not in old_map[key]:
            hl_green.append(map[key].index(c))
        for c in old_map[key]:
          if c not in map[key]:
            if c != 'N':
              hl_red.append(old_map[key].index(c))
        newname = ''
        for i in range(len(map[key])):
          if i in hl_green:
            newname += highlight('greenbg',map[key][i])
          else:
            newname += map[key][i]
        for j in range(len(old_map[key])):
          if j in hl_red:
            newname += highlight('redbg',old_map[key][j])   #strikethrough + highlight
        map[key] = newname
    except:
      pass
map_formatted = print_map(map)

print_side_by_side(rankings_formatted, map_formatted)
print('*************************************')

if lc_controls:
  pass

# save state for comparison next time
try:
  with open("tvscheck.dat",'wb') as f:
    old_lcname = lcname_backup
    old_vcname = vcname_backup
    old_health = health_backup
    old_HW_health = HW_health_backup
    old_rankings = rankings_backup
    old_map = map_backup
    pickle.dump(old_lcname,f)
    pickle.dump(old_vcname,f)
    pickle.dump(old_health,f)
    pickle.dump(old_HW_health,f)
    pickle.dump(old_rankings,f)
    pickle.dump(old_map,f)
except:
  print("Not able to save to file tvscheck.dat")

