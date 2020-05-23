"""
SQL code for query a DB is embedded inside the Python wrapper
"""
#
import shutil
import csv
import sys
import os
import operator
import tempfile
import time
from datetime import datetime
from datetime import date
from pathlib import Path
from email.mime.text import MIMEText
import argparse
import cProfile
from boltons import iterutils
import yagmail
from tqdm import tqdm

try:
    import pyodbc
except ImportError:
    pass

#
# function def's
#

def create_message(sender, to_, subject, message_text):
    """Create a message for an email.
  Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.
  Returns:
    An object containing a base64url encoded email object.
    """
    message1 = MIMEText(message_text)
    message1['to'] = to_
    message1['from'] = sender
    message1['subject'] = subject

    return message1.as_string()


def create_titles(s_s):
    """
    title string
    """
    title_str = []
    for t_t in s_s:
        title_str.append(t_t)
    return title_str


def dir_from_date(d_d, s_s, w_d):
    """
    check for presence and create directories
    """
    dirdate = ''
    dirname = ''
    if s_s == 'y':
        dirdate = str(time.strptime(d_d, "%Y-%m-%d")[0])
        dirname = os.path.join(w_d, dirdate)
    else:
        if s_s == 'ym':
            dirdate = str(time.strptime(d_d, "%Y-%m-%d")[0])
            dirname = os.path.join(w_d, dirdate)
            if not os.path.isdir(dirname):
                try:
                    os.mkdir(dirname)
                except OSError:
                    print('\n\ncreation of the directory %s failed' % dirname, datetime.now())
            month_string = str(time.strptime(d_d, "%Y-%m-%d")[1])
            if len(month_string) == 1:
                month_string = '0'+month_string
            dirdate = str(time.strptime(d_d, "%Y-%m-%d")[0])+'/'+month_string
            dirname = os.path.join(w_d, dirdate)
            if not os.path.isdir(dirname):
                try:
                    os.mkdir(dirname)
                except OSError:
                    print('\n\ncreation of the directory %s failed' % dirname, datetime.now())
        else:
            pass
# uncomment code below if it is necessary to create more nested directories
#            dirdate = str(time.strptime(d_d, "%Y-%m-%d")[0])\
#                          +'/' +str(time.strptime(d_d, "%Y-%m-%d")[1])\
#                                    +'/' +str(time.strptime(d_d, "%Y-%m-%d")[2])
#            dirname = os.path.join(w_d, dirdate)
#        try:
#            os.mkdir(dirname)
#        except OSError:
#            print('\n\ncreation of the directory %s failed' % dirname, datetime.now())

    return dirname


def append_row_to_table(table, tuple_):
    """
    appends one row in a .csv sheet
    """
    row = []
    row.append(tuple_[0])
    row.append(tuple_[1])
    row.append(tuple_[2])
    row.append(tuple_[3])
    row.append(tuple_[4])
    row.append(tuple_[5])
    table.append(row)
    return table


def tickers_string_comma_separated(string):
    """
    creates a string with comma-separated list of tickers
    """
    result = ''
    list_ = string[:-1].split(',')
    list1 = []
    for t_1 in list_:
        if t_1 not in list1: # uniqueness check
            list1.append(t_1)
    list1 = sorted(list1)
    for t_2 in list1:
        if t_2:
            result += t_2+', '
    return result[:-2]


def main(start_date_, working_dir_, nblocks_, email_notification_, top_, archive=False):
    """
    The parametrized main function for CLI in the cloud
    """
# use the following commands on Mac:
#  git status; git pull; git add test.py;
# git commit -m "Art's SQL/Python script update"; git push
# to update the script in the cloud
# /anaconda3/bin/python test.py
# --start-date 1990-01-01 --working-directory ./temp/ --nblocks 100 --archive
# to launch the script (--email-notification -- another flag)
# on Mac terminal from the dir where you have test.py
# comand line arguments; use comments below as an example
# TOP = 10000000
# reduce TOP value to 10 for debugging; put it to inf for a full run
# DATE = '2017-01-01' --  'from' parameter for historical pricing data
# WORKING_DIR = './dataDB/'\
#    +str(time.strftime("%Y-%m-%d"))+'/'
# dir where all outputs go; it can be dated as above
# NBLOCKS = 100
# pricing data are very long queries; they need to be partitioned in blocks
# as a separate project, optimize queries
#
#
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals
# pylint: disable=too-many-arguments
#
    top = top_
    date_from = start_date_
    nblocks = nblocks_
    cwd = os.path.realpath(os.path.dirname(__file__)) # instead of os.getcwd(), which is './'
    working_dir = working_dir_
# empty the whole working dir
    for root, dirs, files in os.walk(working_dir):
        for f_f in files:
            os.unlink(os.path.join(root, f_f))
        for d_d in dirs:
            shutil.rmtree(os.path.join(root, d_d))
    shutil.copy(os.path.join(cwd, 'master_file_joe.csv'), working_dir)
    shutil.copy(os.path.join(cwd, 'ManualLookUpOfTickers.csv'), working_dir)
    shutil.copy(os.path.join(cwd, 'test.py'), working_dir)
#
    database = 'xxx'
    server = 'xxx.xxx.xxx'
    username = 'xxx'
    password = 'xxx'
# Authentication: SQL Server Authentication
# NOTE: The following works on a Mac with the MSSQL 13 driver installed - it is here as the
# default because Art's Anaconda environment doesn't show a non-empty list of drivers from
# pyodbc
    driver = '/usr/local/lib/libmsodbcsql.13.dylib' # '{ODBC Driver 13 for SQL Server}'
    drivers = [item for item in pyodbc.drivers()]
    if drivers:
        driver = drivers[0]
#print('driver:{}'.format(driver))
#
    cnxn = pyodbc.connect('DRIVER=' + driver +
                          ';SERVER=' + server +
                          ';PORT=xxx;DATABASE=' + database +
                          ';UID=' + username +
                          ';PWD=' + password)
    cursor_ = cnxn.cursor()
    refinitiv_data_n_columns = 8
    s_s = ''
    if top is not None:
        s_s = ''' TOP '''+str(top)
# presented below is a sample SQL query to access a dataprovider
# to transfer the input data for ML/DS modeling 
    query = '''SELECT'''+s_s+'''
            A.SecCode                           -- SecCode      -- 0
--  ,       MR1.ID
,           G.TICKER                            -- ticker1      -- 1
,           K.TICKER                            -- ticker2      -- 2
-- ,        G1.EXCHANGE
,           MR1.Country                         -- country      -- 3
,           G1.StartDate                        -- from         -- 4
,           G1.EndDate                          -- to           -- 5
,           K1.TICKER                           -- ticker3      -- 6
--,         I.STATUS
,           I.SECTYPE           AS CURRSECTYPE  -- type         -- 7
,           MR1.NAME            AS CURRNAME     -- current name -- 8
,           I.ISSUER            AS CURRENTISSUE -- current name -- 9
,           G1.ISSUER           AS PITISSUER    -- point-in-time name -- 10

                FROM            SecMstrX                        A

                JOIN            SECMAPX             M
                                ON                  M.SECCODE = A.SECCODE
                                AND                 M.VenType = 1       -- IDC
                                AND                 TYPE_ = 1           -- NorthAmer Equity
                                AND                 M.EXCHANGE <> 2

                                -- AND     M.RANK = 1   -- VIEW ALL (commented out) OR CURRENT ONLY
                                -- AND     A.COUNTRY = 'USA' -- comment this out for ADR's

                JOIN            prc.PrcTKChg                    K
                                ON                  M.VENCODE = K.Code

                JOIN            prc.PrcScChg        G
                                ON                  G.CODE =    K.CODE
                                AND                 ISNULL(G.ENDDATE,'1/1/2059')
                                BETWEEN             K.STARTDATE AND ISNULL(K.ENDDATE,'1/1/2059')

                --JOIN PRCCODE2 Y
                --ON Y.TYPE_ = 2 AND ASCII(G.EXCHANGE) = Y.CODE

                JOIN            prc.PRCINFO         I
                                ON                  I.CODE =    G.CODE
                                AND                 I.SECTYPE   NOT IN ('X','P','E','I','S','U','W','0','7','T','Q','R','V')

                JOIN            SECMAPX             MP1
                                ON                  MP1.VENCODE =   I.CODE
                                AND                 MP1.RANK =      M.RANK
                                AND                 MP1.VENTYPE =   1
                                AND                 MP1.EXCHANGE =  M.EXCHANGE

                JOIN            SECMSTRX            MR1
                                ON                  MR1.SECCODE =   MP1.SECCODE
                                AND                 MR1.TYPE_ =     1

                JOIN            SECMAPX             MP2
                                ON                  MP2.SECCODE =   MR1.SECCODE
                                AND                 MP2.VENTYPE = 1
                                AND                 MP2.RANK =      M.RANK

                JOIN            prc.PRCTKCHG        K1
                                ON                  K1.CODE =       MP2.VENCODE
                                --AND ISNULL(K1.ENDDATE,'1/1/2059') BETWEEN K.STARTDATE AND ISNULL(K.ENDDATE,'1/1/2059')

                JOIN            prc.PRCSCCHG        G1
                                ON                  G1.CODE =       K1.CODE
                                AND                 ISNULL(G1.ENDDATE,'1/1/2059')
                                BETWEEN             K1.STARTDATE    AND     ISNULL(K1.ENDDATE,'1/1/2059')

                 WHERE          MR1.Country = 'USA'

                 ORDER BY       MR1.ID, G1.STARTDATE
                 '''
# output the query string to a file
    with open(os.path.join(working_dir, 'query_master_table.sql'), "w") as query_file:
        query_file.write(query)
    print('\n\nexecuting the query....', datetime.now())
    result = None
    keep_trying_to_query = True
    j = 0
    while keep_trying_to_query:
        j += 1 # this counter shows how many times the script tried to re-open connection
        try:
            print('\n\ntrying to execute cursor_.execute(query)....', datetime.now())
            cursor_.execute(query)
            try:
                print('\n\ntrying to execute result = cursor_.fetchall()....', datetime.now())
                result = cursor_.fetchall()
                keep_trying_to_query = False
            except Exception as err:
                print('\n\nexception #1 for result = cursor_.fetchall()', err, datetime.now(), j)
                try:
                    cursor_.close()
                    cnxn.close()
                    time.sleep(2*j)
                    print("\n\nre-opening server connection....", datetime.now())
                    cnxn = pyodbc.connect('DRIVER='+driver+
                                          ';SERVER='+server+
                                          ';PORT=xxx;DATABASE='+database+
                                          ';UID='+username+
                                          ';PWD='+password)
                    cursor_ = cnxn.cursor()
                except Exception as err:
                    print('\n\nexception #2 while re-connecting', err, datetime.now(), j)
        except Exception as err:
            print('\n\nexception #3 for cursor_.execute(query)', err, datetime.now(), j)
            try:
                cursor_.close()
                cnxn.close()
                time.sleep(2*j)
                print("\n\nre-opening server connection....", datetime.now())
                cnxn = pyodbc.connect('DRIVER='+driver+
                                      ';SERVER='+server+
                                      ';PORT=xxx;DATABASE='+database+
                                      ';UID='+username+
                                      ';PWD='+password)
                cursor_ = cnxn.cursor()
            except Exception as err:
                print('\n\nexception #4 while re-connecting', err, datetime.now(), j)

    tickers = []
    print('\n\nWRITING MASTER TABLE (.csv file)....', datetime.now())
    if result:
        with tqdm(total=len(result), file=sys.stdout) as pbar:
            table_master = []
            table_merged = []
            for row in result:
                pbar.set_description('progress at %s' % datetime.now())
                pbar.update(1)
#
#            A.SecCode                           -- SecCode      -- 0
#--  ,       MR1.ID
#,           G.TICKER                            -- ticker1      -- 1
#,           K.TICKER                            -- ticker2      -- 2
#-- ,        G1.EXCHANGE
#,           MR1.Country                         -- country      -- 3
#,           G1.StartDate                        -- from         -- 4
#,           G1.EndDate                          -- to           -- 5
#,           K1.TICKER                           -- ticker3      -- 6
#--,         I.STATUS
#,           I.SECTYPE           AS CURRSECTYPE  -- type         -- 7
#,           MR1.NAME            AS CURRNAME     -- current name -- 8
#,           I.ISSUER            AS CURRENTISSUE -- current name -- 9
#,           G1.ISSUER           AS PITISSUER    -- point-in-time name -- 10
#
                row1 = []
                row3 = []
                date_to = datetime.date(datetime.now())
                if row[5] is not None:                  # to
                    date_to = datetime.date(row[5])
                else:
                    date_to = datetime.date(datetime.now())
                if date_to > datetime.date(datetime.now()):
                    date_to = datetime.date(datetime.now())
#
                ticker_choices = [str(row[6]), str(row[2]), str(row[1])]
                ticker_choices1 = []
                for t_t in ticker_choices:
                    if t_t not in ticker_choices1:
                        ticker_choices1.append(t_t)
                ticker_choices1 = sorted(ticker_choices1, key=len)
                tickers = ''
                for t_t1 in ticker_choices1:
                    if 'ZZZ' not in t_t1:
                        if t_t1:
                            tickers += t_t1+', '
                        else:
                            tickers += 'error'+', '
                tickers = tickers[:-2]
                row1.append(ticker_choices[0])          # ticker1
                row1.append(str(row[8]))                # point-in-time co.name
                row1.append(str(date_to))               # to
#
                row1.append(str(row[0]))                # SecCode
                row3.append(int(row[0]))                # SecCode as int for sorting
                row1.append(datetime.date(row[4]))      # from
                row3.append(datetime.date(row[4]))
                row1.append(date_to)                    # to
                row3.append(date_to)
                row1.append(str(row[8]))                # point-in-time co.name
                row1.append(tickers)                    # historical record of tickers
                row3.append(tickers)
                row1.append(str(row[9]))                # current co.name
                row3.append(str(row[3]))                # country
                row1.append(str(row[10]))               # alt co.name
                row1.append(str(row[7]))                # type
                row3.append(str(row[7]))
                table_merged.append(row1)
                table_master.append(row3)

            seccode_max = 0
            for row in table_merged:
                if int(row[3]) > seccode_max:
                    seccode_max = int(row[3])
            list_ = [[] for n in range(seccode_max+1)]
            for row in table_merged:
                list_[int(row[3])].append(row)
            list1 = [[] for n in range(seccode_max+1)]
            for i, sublist in enumerate(list_):
                if sublist:
                    for _, item in enumerate(sublist):
                        if item:
                            if item not in list1[i]:
                                list1[i].append(item)
            table_merged1 = []
            for i, sublist in enumerate(list1):
                if sublist:
                    for _, item in enumerate(sublist):
                        if item:
                            table_merged1.append(item)

            seccode_max = 0
            for row in table_master:
                if int(row[0]) > seccode_max:
                    seccode_max = int(row[0])
            list_ = [[] for n in range(seccode_max+1)]
            for row in table_master:
                list_[int(row[0])].append(row)
            list1 = [[] for n in range(seccode_max+1)]
            for i, sublist in enumerate(list_):
                if sublist:
                    for _, item in enumerate(sublist):
                        if item:
                            if item not in list1[i]:
                                list1[i].append(item)
            table_master1 = []
            for i, sublist in enumerate(list1):
                if sublist:
                    for _, item in enumerate(sublist):
                        if item:
                            table_master1.append(item)

            print('length of master table = ', len(table_master1))
            print('\n\nprocessing....')

            with open(os.path.join(working_dir, 'master_table.csv'), 'w') as result_file:
                table_master1 = sorted(table_master1, key=lambda item: item[0])
                row_prev = [None for  i in range(5)]
                accumulated_tickers = ''
                table_master2 = []
                nonce = 0
                nonce1 = 1
                i = 0
                for row in table_master1:

                    accumulated_tickers += row[3]+','

                    if str(row[0]) != str(row_prev[0]):
                        if i > 0:
                            table_master2.append('')

                        tuple_ = [row[0], row[1], row[2],
                                  tickers_string_comma_separated(accumulated_tickers),
                                  row[4], row[5]]
                        table_master2 = append_row_to_table(table_master2, tuple_)

                        accumulated_tickers = ''
                        nonce = 0

                    else:

                        if row[1] == row_prev[1] and\
                        row[2] == row_prev[2] and\
                        row[4] == row_prev[4] and\
                        row[5] == row_prev[5]:
                            if nonce == 0:
                                table_master2 = table_master2[:-1]
                                nonce += 1
                                nonce1 += 1
                            if nonce1 == 0:
                                table_master2 = table_master2[:-1]
                                nonce1 += 1

                            tuple_ = [row[0], row[1], row[2],
                                      tickers_string_comma_separated(accumulated_tickers),
                                      row[4], row[5]]
                            table_master2 = append_row_to_table(table_master2, tuple_)
                            accumulated_tickers = ''
                        else:
                            tuple_ = [row[0], row[1], row[2],
                                      tickers_string_comma_separated(accumulated_tickers),
                                      row[4], row[5]]
                            table_master2 = append_row_to_table(table_master2, tuple_)
                            accumulated_tickers = ''
                            nonce1 = 0

                    row_prev = row
                    i += 1
#
                table_master3 = []
                table_master3.append(create_titles([
                    'SecCode'
                    , 'From'
                    , 'To'
                    , 'Ticker'
                    , 'Country'
                    , 'Type'
                    ]))
                table_master3 += table_master2
                w_r = csv.writer(result_file, dialect='excel')
                w_r.writerows(table_master3)

            print('\n\npost-processing 1....', datetime.now())

            with open(os.path.join(working_dir, 'master_file_joe.csv'), 'r') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                nrow = 0
                for row in csv_reader:
# change True to False to use the list
                    if (str(row[3]) in ('C', 'BAC', 'AAPL') or True) and nrow != 0: # skip titles
                        row1 = []
                        row1.append(str(row[3]))
                        row1.append(str(row[4]))
                        row1.append(str(row[2]))
                        for _ in range(refinitiv_data_n_columns):
                            row1.append('') # fill in with blanks for merged .csv
                        for r_1 in row:
                            row1.append(r_1)
                        table_merged1.append(row1)
                    nrow += 1

            print('\n\npost-processing 2....', datetime.now())

            with open(os.path.join(working_dir,
                                   'master_table_merged_art_vs_joe.csv'), 'w') as result_file:
                w_r = csv.writer(result_file, dialect='excel')
                table_merged1 = sorted(table_merged1, key=operator.itemgetter(0, 1, 2))
                table_merged2 = []
                table_merged2.append(create_titles([
                    ''
                    , ''
                    , ''
                    , 'SecCode'
                    , 'From'
                    , 'To'
                    , 'Point-in-time name'
                    , 'Ticker'
                    , 'Alt. name'
                    , 'Current name'
                    , 'Type'
                    , 'ID'
                    , 'FROM'
                    , 'TO'
                    , 'TICKER'
                    , 'NAME'
                    , 'TYPE'
                    ]))
                table_merged2 += table_merged1
                w_r.writerows(table_merged2)

            print('\n\npost-processing 3....', datetime.now())

            tickers_joe = [] # this should be an array of unique tickers
            i = 0
            with open(os.path.join(working_dir, 'master_file_joe.csv'), 'r') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                for row in csv_reader:
                    if  i != 0: # skip titles at i = 0
                        if row[3] not in tickers_joe: # unique tickers
                            tickers_joe.append(row[3])
                    i += 1

            tickers_art = [] # this should be an array of unique tickers
            for row in table_master2:
                if row:
                    tickers_in_secode = row[3].split(',')
                    for t_1 in tickers_in_secode:
                        if t_1 not in tickers_art: # unique tickers
                            tickers_art.append(t_1)

            print('\n\nnumber of unique tickers in the master: ', len(tickers_art), datetime.now())

            if top is None or top > 100000:
# to get a meaningful missing tickers output, top has to be None
                print('\n\npost-processing 4....', datetime.now())

                missing_tickers = []
                for t_j in tickers_joe:
                    if t_j not in tickers_art: # unique tickers
                        missing_tickers.append(t_j)

                missing_tickers1 = []
                for m_t in missing_tickers:
                    if m_t not in missing_tickers1: # unique tickers
                        missing_tickers1.append(m_t)

                print('\n\nnumber of missing tickers: ', len(missing_tickers1), datetime.now())

                tickers_without_suffix = []
                for m_t in missing_tickers1:
                    if m_t.find('.') != -1:
                        m_t = m_t.split('.')[0]
                    else:
                        m_t = m_t[:-1] # try to remove the fused suffix for missing tickers
                    if m_t not in tickers_without_suffix:
                        tickers_without_suffix.append(m_t)
                print('\n\nnumber of missing tickers without suffix: ',
                      len(tickers_without_suffix), datetime.now())

                query = '''SELECT * FROM PRC.PRCSCCHG WHERE TICKER IN (\''''

                for tws in tickers_without_suffix:
                    query += str(tws)+'''\', \''''
                query = query[:-3]
                query += ''')'''

                print('\n\nexecuting second query....', datetime.now())
                with open(os.path.join(working_dir, 'second_query.sql'), 'w') as query_file:
                    query_file.write(query)
                try:
                    print('\n\ntrying to execute cursor_.execute(query)....', datetime.now())
                    cursor_.execute(query)
                except Exception as err:
                    print('\n\nexception #4 for cursor_.execute(query)', err, datetime.now(), j)
                try:
                    print('\n\ntrying to execute result = cursor_.fetchall()....', datetime.now())
                    result = cursor_.fetchall()
                except Exception as err:
                    print('\n\nexception #5 for result = cursor_.fetchall()',\
                          err, datetime.now(), j)

                print('\n\nwriting the master table addendum....', datetime.now())
                with open(os.path.join(working_dir, 'addendum_master_table.csv'), 'w')\
                as result_file:
                    table_addendum = result
                    table_addendum = sorted(table_addendum, key=operator.itemgetter(4))
                    table_addendum1 = []
                    table_addendum1.append(create_titles([
                        'SecCode'
                        , 'Ticker'
                        , 'Ticker'
                        , 'Country'
                        , 'From'
                        , 'To'
                        , 'Ticker'
                        , 'Type'
                        , 'Com Name'
                        , 'Alt Name'
                        , 'Issuer'
                        ]))
                    table_addendum1 += table_addendum
                    w_r = csv.writer(result_file, dialect='excel')
                    w_r.writerows(table_addendum1)

                found_tickers = []
                for row in result:
                    if str(row[4]) not in found_tickers:
                        found_tickers.append(str(row[4]))

                print('\n\nnumber of found tickers: ', len(found_tickers), datetime.now())

                missing_tickers2 = []
                for m_t in missing_tickers1:
                    wosuffix = m_t
                    if wosuffix.find('.') != -1:
                        wosuffix = wosuffix.split('.')[0]
                    else:
                        wosuffix = wosuffix[:-1] # try to remove the fused suffix
                    if wosuffix not in found_tickers and m_t not in found_tickers:
                        # tickers w/o and with suffix
                        missing_tickers2.append(m_t)
                print('\n\nreduced number of missing tickers: ',\
                      len(missing_tickers2), datetime.now())

                found_tickers_manual = []
                if os.path.isfile(os.path.join(working_dir, '../ManualLookUpOfTickers.csv')):
                    with open(os.path.join(working_dir,\
                                           '../ManualLookUpOfTickers.csv')) as csv_file:
                        csv_reader = csv.reader(csv_file, delimiter=',')
                        l_4 = 0
                        for row in csv_reader:
                            if  l_4 > 0: # skip titles
                                if row[2]:
                                    if '?' not in row[3]:
                                        if row[0] not in found_tickers_manual:
                                            found_tickers_manual.append(row[0])
                            l_4 += 1
                print('\n\nnumber of manually found tickers: ',\
                      len(found_tickers_manual), datetime.now())

                missing_tickers3 = []
                for m_t in missing_tickers2:
                    if m_t not in found_tickers_manual:
                        missing_tickers3.append(m_t)

                print('\n\nfinal number of missing tickers: ',\
                      len(missing_tickers3), datetime.now())
                print('\n\nthe fraction of missing tickers: ',\
                      "{0:.2%}".format(len(missing_tickers3)/\
                       (len(tickers_art)+len(missing_tickers3))),\
                      datetime.now())
                print('\n\nwriting missing tickers....', datetime.now())

                with open(os.path.join(working_dir, 'missing_tickers.csv'), 'w') as result_file:
                    w_r = csv.writer(result_file, dialect='excel')

                    missing_tickers3.sort()
                    missing_tickers4 = []
                    with open(os.path.join(working_dir, 'master_file_joe.csv'), 'r') as csv_file:
                        csv_reader = csv.reader(csv_file, delimiter=',')
                        i = 0
                        for row2 in csv_reader:
                            if i != 0: # skip titles at i = 0
                                for row in missing_tickers3:
                                    if row2[3] == row:
                                        row4 = []
                                        row4.append(str(row2[3]))
                                        row4.append(str(row2[4]))
                                        if row4 not in missing_tickers4: # unique entries
                                            missing_tickers4.append(row4)
                            i += 1
                    missing_tickers5 = []
                    missing_tickers5.append(create_titles(['Tickers', 'Co. names']))
                    missing_tickers5 += missing_tickers4
                    missing_tickers5 = sorted(missing_tickers5, key=lambda item: item[0])
                    w_r.writerows(missing_tickers5)

        print('\n\nDOWNLOADING PRICING DATA....', datetime.now())

        seccodes = []
        seccode_max = 0
        with open(os.path.join(working_dir, 'master_table.csv')) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            l_1 = 0
            for row in csv_reader:
                if  l_1 > 0: # skip titles
                    if row:
                        if row[0] not in seccodes: # unique seccodes
                            seccodes.append(row[0])
                            if seccode_max < int(row[0]):
                                seccode_max = int(row[0])
                l_1 += 1

# add seccodes from the addendum and from the manual list
        if top is None:
            if os.path.isfile(os.path.join(working_dir, 'addendum_master_table.csv')):
                with open(os.path.join(working_dir, 'addendum_master_table.csv')) as csv_file:
                    csv_reader = csv.reader(csv_file, delimiter=',')
                    l_2 = 0
                    for row in csv_reader:
                        if  l_2 > 0: # skip titles
                            if row:
                                if row[0] not in seccodes: # unique seccodes
                                    seccodes.append(row[0])
                                    if seccode_max < int(row[0]):
                                        seccode_max = int(row[0])
                        l_2 += 1

            if os.path.isfile(os.path.join(working_dir, '../ManualLookUpOfTickers.csv')):
                with open(os.path.join(working_dir, '../ManualLookUpOfTickers.csv')) as csv_file:
                    csv_reader = csv.reader(csv_file, delimiter=',')
                    l_3 = 0
                    for row in csv_reader:
                        if  l_3 > 0: # skip titles
                            if (row[2] and '?' not in row[3]):
                                for s_1 in row[2].split(','):
                                    if s_1:
                                        if '-' in s_1:
                                            s_3 = s_1.split('-')
                                            for s_2 in range(int(s_3[0]), int(s_3[1])+1):
                                                if s_2 not in seccodes: # unique seccodes
                                                    seccodes.append(s_2)
                                                    if seccode_max < int(s_2):
                                                        seccode_max = int(s_2)
                                        else:
                                            if s_1 not in seccodes: # unique seccodes
                                                seccodes.append(s_1)
                                                if seccode_max < int(s_1):
                                                    seccode_max = int(s_1)
                        l_3 += 1
#
        print('\n\ndistinct seccodes = ', len(seccodes), datetime.now())
        print('\n\nprocessing....', datetime.now())
# another sample SQL query
        query = '''
        --This query returns the fully adjusted Open, High, Low, and Close Pricing data in Local Currency using the Ds2Primqtprc table for North American Equities*/

        SELECT DISTINCT
                            A.SecCode                       -- seccode  new col=0

                  --  ,       MR1.ID
                 --   ,       MR1.NAME AS CURRNAME
                 --   ,       G1.ISSUER AS PITISSUER
                  --  ,       G1.EXCHANGE
                  --  ,       G1.StartDate
                  --  ,       G1.EndDate

                      ,       ISNULL(I.TICKER, K1.TICKER)   -- ticker new col=1

                --    ,       G1.EXCHANGE
                 --   ,       I.ISSUER AS CURRENTISSUE
                  --  ,       I.STATUS
                  --  ,       I.SECTYPE AS CURRSECTYPE
                  --  ,       C1.TotRet
                 --   ,       C1.placeholder

                      ,     C1.Date_               --  market date col=15; new col=2
                      ,     CONVERT( VARCHAR(100) , CAST(C1.Open_   AS MONEY), 1) + N'$'    --  col=16 open;    new col=3
                      ,     CONVERT( VARCHAR(100) , CAST(C1.High    AS MONEY), 1) + N'$'    --  col=17 high;    new col=4
                      ,     CONVERT( VARCHAR(100) , CAST(C1.Low     AS MONEY), 1) + N'$'    --  col=18 low;     new col=5
                      ,     CONVERT( VARCHAR(100) , CAST(C1.Close_  AS MONEY), 1) + N'$'    --  col=19 close;   new col=6
                      ,     C1.Volume                                                       --  col=20 volume;  new col=7
                      ,     C1.TotRet                                                       --  col=21 totret;  new col=8

                      ,     A.Country


                    FROM            SecMstrX                        A

                    JOIN            SECMAPX             M

                                    ON                  M.SECCODE = A.SECCODE
                                    AND                 M.VenType = 1       -- IDC
                                    AND                 TYPE_ = 1           -- NorthAmer Equity
                                    AND                 M.EXCHANGE <> 2

                                    -- AND M.EXCHANGE = 1 AND A.TYPE_ = 1
                                    -- AND     M.RANK = 1   -- VIEW ALL OR CURRENT ONLY
                                    -- AND     A.COUNTRY = 'USA' -- comment this out for ADR's

                    JOIN            Prc.PrcTKChg                    K
                                    ON                  M.VENCODE = K.Code

                    JOIN            PRC.PRcsCCHG        G
                                    ON                  G.CODE =    K.CODE
                                    AND                 ISNULL(G.ENDDATE,'1/1/2059')
                                    BETWEEN             K.STARTDATE AND ISNULL(K.ENDDATE,'1/1/2059')

                    JOIN            PRC.PRCTKCHG        K1
                                    ON                  K1.CODE =       K.CODE

                    JOIN            PRC.PRCDLY          C1
                                    ON                  C1.CODE =       K1.CODE

                    JOIN            PRC.PRCINFO         I
                                    ON                  I.CODE = G.CODE

                    WHERE
                                    A.Country='USA' AND
                                    A.SECCODE          IN ('''
#
        block_size = int(len(seccodes)/nblocks)+1
        date_now = str(datetime.date(datetime.now())).split('-')
        year_string = date_now[0]
        month_string = date_now[1]
        day_string = date_now[2]
        date_now_int = int(year_string+month_string+day_string)
        date_from_int = int(date_from.replace('-', ''))
        with tqdm(total=nblocks, file=sys.stdout) as pbar:
            for seccodeblock in list(iterutils.chunked_iter(seccodes, block_size)):
                pbar.set_description('progress at %s' % time.strftime("%c"))
                pbar.update(1)
                list_ = [[] for n in range(date_now_int-date_from_int+1)]
                query_seccodes = ''
                print('\n\nseccodeblock length = ', len(seccodeblock), datetime.now())
                for s_c in seccodeblock:
                    query_seccodes += str(s_c) + ''','''
                query_seccodes = query_seccodes[:-1]
                query_date = '''CAST(C1.Date_ AS DATETIME)>= \'''' + date_from + '''\''''
                composed_query = query +\
                                query_seccodes + ''')\n\nAND\n\n''' +\
                                query_date + '''\n\nORDER BY C1.Date_'''
                with open(os.path.join(working_dir, 'query_pricing_data.sql'), 'w') as query_file:
                    query_file.write(composed_query)
                result = None
                keep_trying_to_query = True
# the query might fail because the computer got moved to a different location,
# which resulted in IP change; in this case, try to re-open the connection, then re-do the query
                j = 0
                while keep_trying_to_query:
                    j += 1
                    try:
                        print('\n\ntrying to execute cursor_.execute(COMPOSED_query)....',
                              datetime.now())
                        cursor_.execute(composed_query)
                        try:
                            print('\n\ntrying to execute result = cursor_.fetchall()....',
                                  datetime.now())
                            result = cursor_.fetchall()
                            keep_trying_to_query = False
                        except Exception as err:
                            print('\n\nexception #6 for result = cursor_.fetchall()',
                                  err, datetime.now(), j)
                            try:
                                cursor_.close()
                                cnxn.close()
                                time.sleep(2*j)
                                print("\n\nre-opening server connection....", datetime.now())
                                cnxn = pyodbc.connect('DRIVER='+driver+
                                                      ';SERVER='+server+
                                                      ';PORT=xxx;DATABASE='+database+
                                                      ';UID='+username+
                                                      ';PWD='+password)
                                cursor_ = cnxn.cursor()
                            except Exception as err:
                                print('\n\nexception #7 while re-connecting',\
                                      err, datetime.now(), j)
                    except Exception as err:
                        print('\n\nexception #8 for cursor_.execute(COMPOSED_query)',
                              err, datetime.now(), j)
                        try:
                            cursor_.close()
                            cnxn.close()
                            time.sleep(2*j)
                            print("\n\nre-opening server connection....", datetime.now())
                            cnxn = pyodbc.connect('DRIVER='+driver+
                                                  ';SERVER='+server+
                                                  ';PORT=xxx;DATABASE='+database+
                                                  ';UID='+username+
                                                  ';PWD='+password)
                            cursor_ = cnxn.cursor()
                        except Exception as err:
                            print('\n\nexception #9 while re-connecting', err, datetime.now(), j)
#
                if result:
                    print("\n\nquery produced %d rows" % len(result), datetime.now())
                    tot_ret_prev = [0.0 for n in range(seccode_max+1)]
                    for row in result:
#                          A.SecCode              -- seccode  new col=0
#              --  ,       MR1.ID
#             --   ,       MR1.NAME AS CURRNAME
#             --   ,       G1.ISSUER AS PITISSUER
#              --  ,       G1.EXCHANGE
#              --  ,       G1.StartDate
#              --  ,       G1.EndDate
#                ,       K1.TICKER                -- ticker new col=1
#            --    ,       G1.EXCHANGE
#             --   ,       I.ISSUER AS CURRENTISSUE
#              --  ,       I.STATUS
#              --  ,       I.SECTYPE AS CURRSECTYPE
#              --  ,       C1.TotRet
#             --   ,       C1.placeholder
#                ,       C1.MarketDate            --  col=15 market date; new col=2
#                , C1.Open                        --  col=16 open; new col=3
#                , C1.High                        --  col=17 high; new col=4
#                , C1.Low                         --  col=18 low; new col=5
#                , C1.Close                       --  col=19 close; new col=6
#                ,  C1.Volume                     --  col=20 volume; new col=7
#                ,  C1.TotRet                     --  col=21 totret; new col=8
#               ,       A.Country
#
                        row3 = []
                        row3.append(int(row[0]))        # SecCode
                        row3.append(row[1])             # ticker
                        if row[2] is not None:
                            date1 = str(row[2])[:-9]    # market date
                            row3.append(date1)
                        else:
                            row3.append('-1.0')
                        if row[3] is not None:
                            row3.append(row[3])         # open
                        else:
                            row3.append('-1.0')
                        if row[4] is not None:
                            row3.append(row[4])         # high
                        else:
                            row3.append('-1.0')
                        if row[5] is not None:
                            row3.append(row[5])         # low
                        else:
                            row3.append('-1.0')
                        if row[6] is not None:
                            row3.append(row[6])         # unadjusted close
                        else:
                            row3.append('-1.0')
                        if row[7] is not None:
                            row3.append(row[7])         # volume
                        else:
                            row3.append('-1.0')
                        if row[8] is not None:          # TotRet
                            daily_return = tot_ret_prev[int(row[0])]
                            if daily_return:
                                daily_return = (row[8]-daily_return)/daily_return
                            row3.append("{0:.3%}".format(daily_return))
                            tot_ret_prev[int(row[0])] = row[8]
                        else:
                            row3.append('-1.0')
                        if row[9] is not None:
                            row3.append(row[9])         # Country
                        else:
                            row3.append('need USA')

                        idx = int(row[2].strftime('%Y%m%d'))
                        if row3 not in list_[idx-date_from_int]:
                            list_[idx-date_from_int].append(row3)
#
                for i, i_t in enumerate(list_):
                    if i_t:
                        s_1 = str(i+date_from_int)
                        year = s_1[:-4]
                        month = s_1[4:-2]
                        day = s_1[6:]
                        date2 = year+'-'+month+'-'+day
                        table1 = []
                        table2 = []
                        ofp = os.path.join(dir_from_date(date2, 'ym', working_dir), date2+'.csv')
                        if not os.path.isfile(ofp):
                            table2.append(create_titles([
                                'SecCode'
                                , 'Ticker'
                                , 'Date'
                                , 'Open'
                                , 'High'
                                , 'Low'
                                , 'Close, unadjusted'
                                , 'Volume'
                                , 'Daily return'
                                , 'Country'
                                ]))
                        for _, item in enumerate(i_t):
                            if item not in table1:
                                table1.append(item)
                        table1 = sorted(table1, key=operator.itemgetter(0, 1))
                        table2 += table1
                        with open(ofp, 'a') as result_file:
                            w_r = csv.writer(result_file, dialect='excel')
                            w_r.writerows(table2)
#
        if archive:
            now = str(date.today())
            print('\n\ncompressing output and timestamping....', datetime.now())
            file_name = 'refinitiv_qa_direct_qai_master_and_pricing_tables_'+now
            print('archive = ', file_name, datetime.now())
            shutil.make_archive(file_name, 'zip', working_dir)

            print('\n\nmoving the data to the timestamped repository....', datetime.now())
            src = cwd
            data_repo = os.path.join(src, 'RefinitivDataRepository')
            if not os.path.exists(data_repo):
                os.mkdir(data_repo)
            if not os.path.isdir(data_repo):
                raise Exception(f'Data repository is not a directory: {data_repo}')

            output_file_staging_path = os.path.join(src, file_name +'.zip')
            output_file_path = Path(os.path.join(data_repo, file_name +'.zip'))
            print('OUTPUT_FILE_STAGING_PATH = ', output_file_staging_path,
                  'OUTPUT_FILE_PATH', output_file_path)
            if os.path.isfile(output_file_staging_path):
                if os.path.isfile(output_file_path):
                    new_file_size = os.stat(output_file_staging_path).st_size
                    old_file_size = os.stat(output_file_path).st_size
                    print('\n\nnew zip size = ', new_file_size, '\told_file_size = ', old_file_size)
                    if new_file_size > old_file_size:
                        os.remove(output_file_path)
                        shutil.move(output_file_staging_path, output_file_path)
                else:
                    shutil.move(output_file_staging_path, output_file_path)

        if email_notification_:
            print('\n\nemailing the confirmation and the link to\
                  compressed data to the author....',
                  datetime.now())
            alert = '''This is to notify that new compressed data set was
            uploaded to a google drive....'''
            email = 'Alert time: ' + time.strftime("%c") +'\n' + alert
            client_email = ['xxx@yyy', 'xxx1@yyy']
#    MESSAGE = create_message('artemponomarevjetski@gmail.com',\
#                            CLIENT_EMAIL, 'Completion alert', EMAIL)
            yagmail.SMTP('artemponomarevjetski@gmail.com').\
            send(client_email, 'Completion alert', email)
            print('\n\nemailed to the user:\n'+alert, datetime.now())

    print('\n\nexiting....', datetime.now())


def is_valid_date_string(maybe_date_string: str) -> str:
    """
    Errors out if maybe_date_string is not a valid date string (as expected by this
    script). Otherwise, simply returns the string.
    """
    time.strptime(maybe_date_string, '%Y-%m-%d')
    return maybe_date_string

if __name__ == '__main__':
    PR = cProfile.Profile()
    PR.enable()
#
    PARSER = argparse.ArgumentParser(description='Input parameters: ')
    PARSER.add_argument(
        '-s',
        '--start-date',
        type=is_valid_date_string,
        default=time.strftime('%Y-%m-%d'),
        help='Date from which we should retrieve pricing data through Refinitiv',
    )
    PARSER.add_argument(
        '-d',
        '--working-directory',
        type=str, # make it start with ./ and end with /
        default=None,
        help='call Art at 409-443-4701'
    )
    PARSER.add_argument(
        '-n',
        '--nblocks',
        type=int,
        default=100,
        help='long SQL queries need to be partitioned into smaller ones,\
        or the risk of connection drop increases'
        )
    PARSER.add_argument(
        '-e',
        '--email-notification',
        action='store_true',
        help='Set this to send an e-mail notification when job is complete',
    )
    PARSER.add_argument(
        '-m',
        '--top',
        type=int,
        default=None,
        help='Limit on the query against Refinitive database',
    )
    PARSER.add_argument(
        '--archive',
        action='store_true',
        help='Set this flag to store a ZIP archive of the working_directory',
    )

    ARGS = PARSER.parse_args()

    WORKING_DIRECTORY = (
        ARGS.working_directory if ARGS.working_directory is not None else tempfile.mkdtemp()
    )

    print(f'Working directory: {WORKING_DIRECTORY}')

    main(
        ARGS.start_date,
        WORKING_DIRECTORY,
        ARGS.nblocks,
        ARGS.email_notification,
        ARGS.top,
        ARGS.archive,
    )
    PR.disable()
    PR.print_stats()
#
##########################
#
# user defined classes
#
# data analysis class
#
# TODO: build objects for missing ticker; put this in the main
#i = 0
#for t in missing_tikers3:
#    print(t)
#    T = TickerNeighborhood(ticker=t[0])
#    T.current_name = t[1]
#    print(T)
#    list_of_suggested_tickers_for_addendum=[]
#    list_of_suggested_tickers_for_addendum
#=T.analyze_the_neighborhood_of_T_while_keeping_in_mind_joes_master_table('master_table_joe.csv')
#
class TickerNeighborhood:
    """For unfriendly tickers, connect the dots by analysing data related somehow\
        to the given ticker
      TODO(Art): Finish the implementation
     """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    # pylint: disable=too-few-public-methods
    # pylint: disable-msg=too-many-locals
    def __init__(self, ticker='BAC', seccode=None, from_=None, to_=None, cusip=None, sedol=None
                 , issuer=None, full_ticker=None, base_ticker=None, group=None, series=None
                 , exchange=None, point_in_time_name=None, country=None, current_name=None
                 , type_=None, id_=None, name=None, date_=None, open_=None, high=None, low=None
                 , close=None, adjusted_previous_close=None, volume=None
                 , adj_close_vs_adj_prev_close_minus_one=0.0):

        self.ticker = ticker
        self.seccode = seccode
        self.from_ = from_
        self.to_ = to_
        self.cusip = cusip
        self.sedol = sedol
        self.issuer = issuer
        self.full_ticker = full_ticker
        self.base_ticker = base_ticker
        self.group = group
        self.series = series
        self.exchange = exchange
        self.point_in_time_name = point_in_time_name
        self.country = country
        self.current_name = current_name
        self.type_ = type_
        self.id_ = id_
        self.name = name
        self.date_ = date_
        self.open_ = open_
        self.high = high
        self.low = low
        self.close = close
        self.adjusted_previous_close = adjusted_previous_close
        self.volume = volume
        self.adj_close_vs_adj_prev_close_minus_one = adj_close_vs_adj_prev_close_minus_one

    @staticmethod
    def tic_nhood(ticker, s_s, working_dir):
        """Analyze_the_neighborhood_of_ticker_while_keeping_in_mind_joes_master_table:
            For unfriendly tickers, connect the dots by analysing data related somehow
            to the given ticker"""
        nrow = 0
        table2 = []
        with open(working_dir+s_s, 'r') as csv_file1:
            csv_reader1 = csv.reader(csv_file1, delimiter=',')
            for row4 in csv_reader1:
                if nrow != 0 and str(row4[2]) == ticker: # skip titles
                    row6 = []
                    row6.append(str(row4[3]))
                    row6.append(str(row4[4]))
                    row6.append(str(row4[2]))
                #    for i_i in range(DATA_N_COLUMNS):
                 #       row6.append('') # TODO
                    for r_r in row4:
                        row6.append(r_r)
                    table2.append(row6)
                nrow += 1
        return table2
