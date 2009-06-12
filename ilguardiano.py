#!/usr/bin/env python
# -*- coding: utf-8 -*-

__module_name__ = "IlGuardiano"
__module_version__ = "0.2.0"
__module_description__ = "Modulo Python per kickare chi dice parole sgradevoli"
__module_author__ = "Stefano Zamprogno <mie.iscrizioni@gmail.com>"

import weechat
import shelve
import os
import time
import sys
import random
import string

weechat.register("ilguardiano.py", "0.2.0", "",
                            "Gestione Bestemmie v.0.2.0", "UTF8")
# definizione dati di default
parolacce = {'dio porco':'Contegno! mi consenta...',
             'dioporco':'Contegno! mi consenta...',
             'diocan':'Contegno! mi consenta...',
             'dio can':'Contegno! mi consenta...',
             'porco dio':'Contegno! mi consenta...',
             'porcoddio':'Contegno! mi consenta...',
             'porcodio':'Contegno! mi consenta...',
             'dio stracan':'Contegno! mi consenta...',
             'dio bastardo':'Contegno! mi consenta...',
             'madonna putana':'Contegno! mi consenta...',
             'madonna puttana':'Contegno! mi consenta...',
             'orco dio':'Contegno! mi consenta...',
             'orcoddio':'Contegno! mi consenta...',
             'madonna troia':'Contegno! mi consenta...',
             'mandona puttana':'Contegno! mi consenta...',
             'madona vacca':'Contegno! mi consenta...',
             'madona vaca':'Contegno! mi consenta...',
             'madonna vaca':'Contegno! mi consenta...',
             'madona troia':'Contegno! mi consenta...',
             'codio':'Contegno! mi consenta...',
             'coddio':'Contegno! mi consenta...',
             'madona putana':'Contegno! mi consenta...',
             'dio infame':'Contegno! mi consenta...',
             '!list':'Niente files qui...',
             '!file':'Niente files qui...'
            }

# network/canali da monitorare
chans = {'azzurra':set(['#archlinux','#nokia','#ubuntu','#energiasolare']),
         'freenode':set(['#archlinux.it',])}

# devo killare anche gli op?
killop = False
# formato di killed
# {(tupla:nick,chan,network):[lista:(tupla:hour,min,sec)*n]}
# es.
#{('AserTo', '#nokia', 'azzurra'): [(7, 45, 26), (7, 45, 28)],
# ('L0cutus', '#nokia', 'azzurra'): [(7, 45, 26), (7, 45, 28), (7, 45, 35)],
# ('kk', '#archlinux', 'azzurra'): [(7, 45, 26), (7, 45, 28), (7, 45, 35)]}
killed = {}
mynick = 'L0cutus'
kick_queue = set()
op = False
tchan = None
tsrv = None

# -----------------------------------------------------------
# Non modificare oltre questa linea--------------------------
# -----------------------------------------------------------

db = shelve.open('.ilguardiano.db')

if 'chans' in db:
    # su che canali e' attivo il guardiano
    chans = db['chans']

if 'parolacce' in db:
    parolacce = db['parolacce']

if 'killop' in db:
    killop = db['killop']

def hook_mode_cb(server, args):
    global op,mynick
    if '+o' not in args:
        return weechat.PLUGIN_RC_OK
    res = args.split(" ")
    weechat.prnt("Len args: %s" % len(res), '#tst', 'azzurra')
    weechat.prnt("Res: %s" % res, '#tst', 'azzurra')
    null, null, chan, mode, nick = args.split(" ", 5)
    weechat.prnt("nick: %s\nchan; %s" % (nick,chan), '#tst', 'azzurra')
    if (server in chans and chan in chans[server]):
        if nick == mynick:
            if not op and mode == '+o':
                op = True
                weechat.add_timer_handler(20, "hook_timer_cb") # 20sec di op
            elif mode == '-o':
                op = False
    return weechat.PLUGIN_RC_OK


def hook_msg_cb(server, args):
    global op,tchan,tsrv,mynick
    null, chan, testo = args.split(":", 2)
    mask, null, chan = chan.strip().split(" ", 2)
    nick, mask = mask.split("!", 1)
    network = server
    testo = testo.lower().strip()
    isop = False
    # se non si possono killare gli op
    # occorre verificare se l'user e' un op
    if not killop:
        nicks = weechat.get_nick_info(network, chan)
        if nicks:
            for nk in nicks.keys():
                if nick == nk:
                    flg = nicks[nk]['flags']
                    if flg == 4:
                        isop = True # e' un op
                        break
    # l'unica volta in cui non si puo kickare e' quando
    # l'user e' un op E non e' attivo il flag killop
    # isop  killop risultato
    #   1      1      1
    #   1      0      0
    #   0      1      1
    #   0      0      1
    if not (isop and (not killop)):
        # se il network e' tra quelli osservati e il canale e'
        # tra quelli monitorati...
        if (network in chans and chan in chans[network]):
            for p in parolacce.keys():
                if p in testo:
                    kick_queue.add((nick,chan,network,parolacce[p]))
                    if not op:
                        tchan = chan
                        tsrv = network
                        weechat.command("/cs op %s %s" % (chan, mynick), '', network)
                    break
    return weechat.PLUGIN_RC_OK

def hook_tmr_queue_cb():
    global op,kick_queue,killed
    if kick_queue:
        for cmd in list(kick_queue):
            if op:
                weechat.command("/kick %s %s" % (cmd[0], cmd[3]), cmd[1], cmd[2])
                if (cmd[0],cmd[1],cmd[2]) not in killed:
                    killed[(cmd[0],cmd[1],cmd[2])] = [(time.time()),]
                else:
                    killed[(cmd[0],cmd[1],cmd[2])].append((time.time()))
                kick_queue.discard((cmd[0], cmd[1], cmd[2], cmd[3]))
    return weechat.PLUGIN_RC_OK

def hook_timer_cb():
    global op,tchan,tsrv,mynick
    op = False
    weechat.command("/cs deop %s %s" % (tchan, mynick), '', tsrv)
    weechat.remove_timer_handler('hook_timer_cb')
    return weechat.PLUGIN_RC_OK

# aggiunge una nuova parolaccia
def hook_addword_cb(server, args):
    dati = list(args.split('-:-',1))
    if len(dati) < 2:
        weechat.prnt("Non hai specificato tutti i parametri!")
    else:
        parolacce[dati[0].lower()] = dati[1]
        weechat.prnt("Aggiunto: %s frase: %s" % (dati[0], dati[1]))
        db['parolacce'] = parolacce
    return weechat.PLUGIN_RC_OK_IGNORE_ALL

# cancella una parolaccia dal dizionario
def hook_delword_cb(server, args):
    if not args.strip():
        weechat.prnt("Non hai specificato tutti i parametri!")
    else:
        del parolacce[args.strip().lower()]
        db['parolacce'] = parolacce
    return weechat.PLUGIN_RC_OK_IGNORE_ALL

# aggiunge una nuovo canale/network
def hook_addchan_cb(server, args):
    dati = args.split(' ', 1)
    if len(dati) < 2:
        weechat.prnt("Non hai specificato tutti i parametri!")
    else:
        netw = dati[0].lower()
        chns = dati[1].lower()
        if netw not in chans:
            chans[netw]=set()

        chns = list(chns.split(','))
        for i in chns:
            chans[netw].add(i,)
        weechat.prnt("Aggiunto network: %s, canale(i): %s" % (netw, chns))
        db['chans'] = chans
    return weechat.PLUGIN_RC_OK_IGNORE_ALL


# cancella un canale/network
def hook_delchan_cb(server, args):
    dati = list(args.split(' ', 1))
    if len(dati) == 1: # cancella tutto il network
        # c'e' il network ?
        if dati[0].lower() in chans:
            del chans[dati[0].lower()]
            db['chans'] = chans
            weechat.prnt("Cancellato server: %s" % dati[0])
        else:
            weechat.prnt("Network non trovato!")
    elif len(dati) == 2: # cancella canali nel network
        netw = dati[0].lower()  # network
        chns = list(dati[1].lower().split(','))  # canali
        # c'e' il network ?
        if netw in chans:
            # esiste il canale da cancellare ?
            for i in chns:
                chans[netw].discard(i)
            db['chans'] = chans
            weechat.prnt("Cancellato/i canale/i: %s" % chns)
        else:
            weechat.prnt("Network non trovato!")
    else:
        weechat.prnt("Errato numero di parametri!")
    return weechat.PLUGIN_RC_OK_IGNORE_ALL

# switcha il flag killop on/off
def hook_swkop_cb(server, args):
    global killop
    killop = not killop
    weechat.prnt("Stato attuale killop= %s" % killop)
    db['killop'] = killop
    return weechat.PLUGIN_RC_OK_IGNORE_ALL

# stampa l'intero archivio parolacce
def hook_pripar_cb(server, args):
    weechat.prnt("Parolacce:")
    for i in parolacce:
        weechat.prnt("%s : %s" % (i, parolacce[i]))
    return weechat.PLUGIN_RC_OK_IGNORE_ALL

# stampa la lista dei killati
def hook_prikilled_cb(server, args):
    weechat.prnt("Lista killati:")
    for i in killed.keys():
        weechat.prnt("Nick: %s, Canale: %s, Server: %s" % (i[0], i[1], i[2]))
        for t in killed[i]:
            weechat.prnt("Time: %s" % (time.localtime(t)))
    return weechat.PLUGIN_RC_OK_IGNORE_ALL

# stampa l'intero archivio canali
def hook_prichan_cb(server, args):
    weechat.prnt("Canali:")
    for i in chans:
        weechat.prnt("%s : %s" % (i, chans[i]))
    return weechat.PLUGIN_RC_OK_IGNORE_ALL

# stampa i dati archiviati
def hook_pridata_cb(server, args):
    hook_prichan_cb('','')
    weechat.prnt('')
    hook_pripar_cb('','')
    weechat.prnt('')
    weechat.prnt('killop: ')
    weechat.prnt(str(killop))
    return weechat.PLUGIN_RC_OK_IGNORE_ALL

# stampa la lista dei comandi disponibili
def hook_prihelp_cb(server, args):
    helps = ("/HELP addword",
             "/HELP delword",
             "/HELP addchan",
             "/HELP delchan",
             "/HELP pripar",
             "/HELP prichan",
             "/HELP pridata",
             "/HELP swkop")
    for i in helps:
        weechat.command(i)
    return weechat.PLUGIN_RC_OK_IGNORE_ALL

weechat.add_timer_handler(2, "hook_tmr_queue_cb")

weechat.add_message_handler("privmsg",
                            "hook_msg_cb")

weechat.add_message_handler("mode",
                            "hook_mode_cb")

weechat.add_command_handler("addword", "hook_addword_cb","",
                "bestemmia -:- commento : Aggiunge una nuova"
                " bestemmia alla lista")

weechat.add_command_handler("pripar", "hook_pripar_cb", "",
                ": stampa la lista delle parolacce monitorate")

weechat.add_command_handler("prichan", "hook_prichan_cb","",
                ": stampa la lista dei network/canali monitorati")

weechat.add_command_handler("prihelp", "hook_prihelp_cb", "",
                "Stampa l'help di tutti i comandi'")

weechat.add_command_handler("pridata", "hook_pridata_cb", "",
                ": stampa i dati in archivio")

weechat.add_command_handler("swkop", "hook_swkop_cb", "",
                ": inverte lo switch killop")

weechat.add_command_handler("addchan", "hook_addchan_cb", "",
                "network canale : Aggiunge un nuovo canale "
                "da monitorare alla lista")

weechat.add_command_handler("delchan", "hook_delchan_cb", "",
                "network [canale,canale] : Cancella un "
                "network - canale/i monitorato/i dalla lista")

weechat.add_command_handler("delword", "hook_delword_cb", "",
                "bestemmia : Cancella una bestemmia dalla lista")

weechat.add_command_handler("prikilled", "hook_prikilled_cb", "",
                ": mostra i vari nick che sono stati killati")

weechat.prnt("Plugin IlGuardiano loaded!")
