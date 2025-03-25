---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
language_info:
  name: python
  nbconvert_exporter: python
  pygments_lexer: ipython3
---

# multi-joueur avec redis

{download}`vous aurez besoin du zip qui se trouve ici<./ARTEFACTS-redis.zip>`

on se propose de réaliser un petit jeu multi joueur, et pour cela nous aurons besoin de

* [redis](https://redis.io/), un système de base de données *light* et rapide,
  où les données sont stockées en mémoire; il ne s'agit pas d'un système
  traditionnel, ici pas de SQL ni de stockage sur le disque; il existe bien sûr
  [une librairie Python](https://redis.readthedocs.io/en/latest/) pour
  communiquer avec redis depuis Python
* [pygame](www.pygame.org), et plus accessoirement pour le graphisme et autres
  interactions avec le jeu (qu'on a déjà vu avec le snake)

+++

## architecture

### *process* et isolation

un jeu multi-joueur pose des défis qui vont au-delà de ce qu'on apprend dans un
cours de programmation de base  
en effet on apprend pour commencer à programmer dans un monde fini et isolé -
l'OS appelle ça un *process* - qui **par définition** ne partage aucune donnée
avec les autres programmes qui tournent dans le même ordinateur  
typiquement quand vous écrivez un programme Python et que vous le lancez avec
`python mon_code.py`, tout le code tourne **dans un seul process**  
(sauf si vous faites exprès d'en créer d'autres bien entendu)

### comment partager

du coup lorsqu'on veut faire jouer ensemble, disons deux personnes, on aurait en
théorie le choix entre

* faire tourner tout le jeu, c'est-à-dire les deux joueurs, dans un seul
  process; mais ça impose de jouer tous les deux sur le même ordi, pas glop du
  tout
* du coup ça n'est pas une solution en général, donc c'est beaucoup mieux que
  **chaque joueur lance son propre process**,  
  qui pourront même du coup tourner sur des ordinateurs différents pourvu qu'on s'y prenne correctement

mais avec cette deuxième approche il faut trouver **un moyen d'échanger des informations**:  
chaque process a le contrôle sur la position de son joueur, mais a besoin
d'obtenir les positions des autres joueurs

on va voir comment on peut s'y prendre

### une solution centralisée

l'architecture la plus simple pour établir la communication entre tous les
joueurs consiste à créer un **processus serveur**, auquel les joueurs sont
connectés, selon un diagramme dit en étoile (terme qui prend tout son sens avec
plusieurs joueurs: le serveur est au centre du diagramme) :

```{image} media/processes.excalidraw.svg
:align: center
:height: 450px
```

+++

## étape 0: comprendre le starter code

vous trouverez dans le zip un jeu fonctionnel; c'est très très vaguement
inspiré du jeu du snake: vous controlez un joueur qui se matérialise par une
case carrée que vous bougez avec les fleches du clavier

vous lancez le jeu en faisant

```shell
# ajoutez --help pour voir les options disponibles

python game.py pierre
```

votre première mission consiste donc à lire le code et à comprendre comment il
fonctionne, au moins dans les grandes lignes  
remarquez notamment qu'on a déjà prévu de passer un 'server' au programme en faisant

```shell
python game.py --server localhost pierre
```

mais que pour l'instant ce paramètre n'est pas utilisé

+++

## objectifs du TP

vous devez modifier ce code pour qu'il puisse fonctionner à plusieurs joueurs,
potentiellement sur plusieurs ordinateurs

si vous vous sentez, vous pouvez vous lancer sans indication supplémentaire;
sinon, lisez la suite

## étape 1: installer `redis`

### requirements

pour installer les librairies Python nécessaires, faites

```shell
pip install -r requirements.txt
```

### installation de redis

en plus de la library Python, il vous faudra installer le **serveur** redis  
sur toutes les plateformes, on peut l'installer avec `conda install redis`  
voici aussi à tout hasard d'autres options, selon votre système d'exploitation

`````{tab-set}
````{tab-item} Windows
* autre option: memurai  
  dont l'installation se charge de créer un service microsoft
````

````{tab-item} MacOS
autre option: `brew install redis`
````

````{tab-item} Linux
* redhat/fedora: autre option: `dnf install redis`
* debain/ubuntu: `apt install redis`
````
`````

### pour lancer redis

pour commencer on va travailler uniquement en local (tous les process tournent
sur l'ordinateur local); lancez le serveur redis avec

```shell
redis-server --protected-mode no
```

comme d'habitude, ce process ne se termine pas, donc il va monopoliser le terminal  
il faut le laisser tourner pendant tout le temps du jeu  
lancez un autre terminal pour continuer le travail

### micro-cheatsheet `redis`

quelques astuces pour commencer:

- par défaut, les données rangées dans le serveur (clés aussi bien que valeurs)
  sont des **`bytes`**, donc vous devez les décoder ; vous pouvez également définir
  `decode_responses=True` dans le constructeur `Redis`, ce qui peut simplifier
  votre code
- les exemples les plus simples utilisent simplement `server.set()` et
  `server.get()` ; mais dans notre cas, il faut éviter cette approche, car elle
  ne permet pas d'attacher simplement plusieurs champs à une clé

**voici une toute petite session** pour vous montrer comment ça marche  
je suppose qu'on vient juste de lancer un serveur tout neuf  
pour simplifier on n'utilise qu'un seul interpréteur Python (comme toujours je
vous recommande d'utiliser `ipython`), mais bien sûr vous pouvez essayer tout ça
avec deux process Python différents

```python
from redis import Redis
import json

# connect to server
redis_server = Redis("localhost", decode_responses=True)

# inspect keys - returns an empty list at first
redis_server.keys()

# one can only attach atoms (numbers or strings) to keys
# so we json-encode the data

# to set multiple fields
redis_server.hset('pierre',
  mapping = {
    'position': json.dumps([10, 20]),
    'color': json.dumps([255, 0, 0]),
  })

# to set only one field
redis_server.hset('pierre', 'position', json.dumps([20, 30]))

# to retrieve the full mapping for a key
redis_server.hgetall('pierre')
# -> would return
# {'position': '[20, 30]', 'color': '[255, 0, 0]'}
# remember the values are JSON-encoded

# at that point there is one key in the server (and it's a bytes)
len(redis_server.keys()) == 1

# it's important you make sure you clean up after yourself
# since the keys essentially give the list of players currently in the game
# remove a key
redis_server.delete('pierre')
```

## étape 2: rendre le jeu multi-joueur

il vous faut maintenant modifier le code pour que le rendre multi-joueurs

quelques suggestions dans ce sens:

* il va vous falloir créer une instance du serveur redis (un `redis.Redis()`)
  dans le programme principal
* et passer cette instance à la classe `Player`
* de façon à ce qu'elle puisse tenir le serveur redis au courant de toutes ses
  modifications de position et/ou de couleur (le raccourci clavier `c` permet de
  changer de couleur du joueur)
* une fois que c'est fait, il convient que le programme principal interroge le
  serveur pour connaitre la position des autres joueurs, avant de rafraichir
  l'affichage
* pour faire cela, une voie possible serait d'écrire une classe `Others` (dans un
  fichier `others.py`) dont le travail est d'interroger le serveur pour connaitre
  la position des autres joueurs
* ce qui donnerait un flux de données dans le genre de ceci

  ```{image} media/dataflow.excalidraw.svg
  :align: center
  :height: 450px
  ```

* faites bien attention à ce que les données soient bien nettoyées à la fin du
  programme, sinon vous allez voir des joueurs fantôme (si nécessaire, relancez
  le serveur redis pour repartir sur des bases saines)

bien entendu vous commencez par faire marcher le jeu avec un seul joueur; une
fois que ça fonctionne vous pouvez passer à deux joueurs  
notez que la touche de raccourci `a` permet de passer en mode automatique, où le
joueur se déplace tout seul au hasard

## étape 3: jouer sur plusieurs ordinateurs

jusqu'ici on a fait tourner tous les processus dans le même ordinateur

en vraie grandeur bien sûr, on veut faire tourner ça sur plusieurs ordinateurs

```{image} media/ip-addresses.excalidraw.svg
:align: center
```

pour jouer sur plusieurs ordinateurs, il nous reste quelques étapes - plus de
codage, mais de la mise en place:

### rendre le serveur redis joignable de l'extérieur

on va devoir lancer le serveur redis sur **un des** ordinateurs  
peu importe où il est lancé (ça pourrait même être dans un cloud si on voulait),
mais par contre il faut que les **autres ordinateurs puissent y accéder**

aussi on ne peut plus lancer le serveur redis avec `localhost` (qui est une
adresse uniquement joignable depuis le même ordi); il va falloir utiliser
cette fois une adresse IP visible de l'extérieur; pour cela, faire plutôt

```bash
# jacques lance le serveur comme ceci
redis-server --bind 0.0.0.0
```

### trouver l'adresse IP du serveur

de cette façon le serveur `redis` sera joignable sur l'adresse IP de
l'ordinateur; sur notre exemple c'est `192.168.0.20`, mais comment on le sait ?

selon les systèmes, Jacques lance dans un terminal la commande suivante

`````{tab-set}
````{tab-item} Windows
```shell
ipconfig
```
````

````{tab-item} MacOS
```shell
ifconfig
```
````

````{tab-item} Linux
```shell
ip address show
```
````

`````

et cherche une adresse parmi les intervalles réservés aux adresses privées:

```{admonition} adresses publiques
:class: dropdown admonition-small tip
en effet il est ultra fréquent que les ordinateurs soient derrière un routeur qui NATe les adresses privées en adresses publiques; dans des cas plus rares votre adresse IP est publique, donc pas dans les plages suivantes; en tous cas il s'agit d'une adresse qui ne commence pas par `127.` car celles-là ont une portée locale (*loopback*)
```

| plage | taille |
|-:|:-|
| `192.168.0.0/16` | $2^{16} = 65,536$ adresses
| `172.16.0.0/12` | $2^{20} = 1,048,576$ adresses
| `10.0.0.0/8` | $2^{24} = 16,777,216$ adresses

+++

```{admonition} plus de détails
:class: seealso

plus de détails ici
* <https://ipstack.com/classes-of-private-ip-address>
* le RFC: <https://datatracker.ietf.org/doc/html/rfc1918>
```

+++

### utiliser le même code partout

il va falloir aussi que tout le monde utilise le même code; pour cela vous
pouvez utiliser:

- `git` et `github` - sans doute le plus adapté
- un outil de synchronisation de fichiers comme par exemple `rsync`
- le mail (sans doute le moins adapté !)

```{admonition} compatibilité
:class: dropdown admonition-small
sauf si vous avez réussi à écrire des codes différents, mais qui rangent leurs données de la même façon dans redis...
```

### lancer le jeu

une fois que l'adresse IP est connue, tout le monde peut lancer le jeu avec
```shell
python game.py --server 192.169.0.20 chacun-son-nom-ici
```

et, si tout va bien, on a un jeu multi-joueur qui tourne en réseau

### firewall

il y a toutefois une probabilité que ça ne marche pas du premier coup  
en effet, les ordinateurs sont souvent protégés par un firewall qui bloque
certains ports de communication  
si c'est le cas avec l'ordi de Jacques, il va devoir trouver le moyen 
- soit de débloquer le port 6379 - c'est le port par défaut de redis; demandez à
  google comment faire, en fonction de votre OS
- ou alors de lancer le serveur redis sur un autre port qui serait ouvert sur
  son ordi - auquel cas on pourra lancer le jeu avec `-server 192.168.0.20:443`
  par exemple
