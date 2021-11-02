#!/bin/env python3

import json
import sys
import os

data = json.load(open("family.json"))

people = data["people"]
for pid in people:
	p = people[pid]
	p["_father"] = None
	p["_mother"] = None
	p["_family"] = None
	p["_husband"] = None
	p["_wife"] = None
	p["_kids"] = []
	p["_in_tree"] = None
	p["_grafted"] = False

for pid in people:
	p = people[pid]
	if "lastname" in p:
		br = data["branches"][p["lastname"]]
		if "_count" not in br:
			br["_count"] = 0
		p["_family"] = br
		br["_count"] += 1
	if "father" in p:
		f = people[p["father"]]
		p["_father"] = f
		f["_kids"].append(p)
	if "mother" in p:
		m = people[p["mother"]]
		p["_mother"] = m
		m["_kids"].append(p)

ms = data["marriage"]
for m in ms:
	hid = m["p"][0]
	wid = m["p"][1]
	ph = people[hid]
	pw = people[wid]
	if ph["_wife"]:
		raise f"{hid} is already married"
	if pw["_husband"]:
		raise f"{wid} is already married"

	ph["_wife"] = pw
	pw["_husband"] = ph


def get_max_depth(p):
	d = 0
	for k in p["_kids"]:
		kk = get_max_depth(k) + 1
		if kk > d:
			d = kk
	return d

patriarches = []
pat_depth = -1

for pid in people:
	p = people[pid]
	d = get_max_depth(p)
	if d > pat_depth:
		patriarches = []
		pat_depth = d
	if d == pat_depth:
		patriarches.append(p)


def set_level(p, lvl):
	if "_level" in p:
		if p["_level"] != lvl:
			raise "Level mismatch"
		return

	p["_level"] = lvl
	for k in p["_kids"]:
		set_level(k, lvl + 1)

for p in patriarches:
	set_level(p, 0)

cont = True
max_level = 0
while cont:
	cont = False
	for pid in people:
		p = people[pid]
		if "_level" in p:
			l = p["_level"]
			if max_level < l:
				max_level = l
			continue

		blp = None
		if p["_husband"]:
			blp = p["_husband"]
		elif p["_wife"]:
			blp = p["_wife"]

		if blp and ("_level" in blp):
			p["_level"] = blp["_level"]
			cont = True
			continue

		blp = None
		if p["_father"]:
			blp = p["_father"]
		elif p["_mother"]:
			blp = p["_mother"]

		if blp and ("_level" in blp):
			l = blp["_level"] + 1
			p["_level"] = l
			if max_level < l:
				max_level = l
			cont = True
			continue

		blp = None
		for k in p["_kids"]:
			if "_level" in k:
				blp = k
				break

		if blp:
			p["_level"] = blp["_level"] - 1
			cont = True
			continue

for pid in people:
	p = people[pid]
	if "_level" not in p:
		raise "unleveled person"


def lastname_str(p, pfx = "", sfx = ""):
	if not p["_family"]:
		return ""
	br = p["_family"]
	return pfx + br['p'] + sfx


tree = { }

def put_to_tree(p, node):
	if p["_in_tree"]:
		if p["_in_tree"] != node:
			raise "node mismatch on repopulation"
		return

	if "people" not in node:
		node["people"] = []

	node["people"].append(p)
	p["_in_tree"] = node

	if p["_father"]:
		if "father" not in node:
			n = {}
			n["kids"] = node
			node["father"] = n
		put_to_tree(p["_father"], node["father"])

	if p["_mother"]:
		if "mother" not in node:
			n = {}
			n["kids"] = node
			node["mother"] = n
		put_to_tree(p["_mother"], node["mother"])

def graft_to_tree(p):
	p["_grafted"] = True
	fp = p["_father"]
	mp = p["_mother"]

	if fp and mp:
		tn = fp["_in_tree"]["kids"]

		if not (tn and (tn == mp["_in_tree"]["kids"])):
			raise "nodes mismatch on graft"

		tn["people"].append(p)
		p["_in_tree"] = tn
		return

	if not fp:
		fp = mp
	if not fp:
		return

	pn = fp["_in_tree"]
	if not "own_kids" in pn:
		n = {}
		n["people"] = []
		n["side"] = True
		pn["own_kids"] = n
		if not mp:
			n["father"] = pn
		else:
			n["mother"] = pn

	tn = pn["own_kids"]
	tn["people"].append(p)
	p["_in_tree"] = tn


for pid in people:
	p = people[pid]
	if p["_level"] == max_level:
		put_to_tree(p, tree)

for pid in people:
	p = people[pid]
	if not p["_in_tree"]:
		graft_to_tree(p)

def set_width_and_offset(node, off):
	width = 0
	if "father" in node:
		width += set_width_and_offset(node["father"], off)
	if "mother" in node:
		width += set_width_and_offset(node["mother"], off + width)
	if width == 0:
		width = 1
	node["_width"] = width
	node["_off"] = off
	return width

set_width_and_offset(tree, 0)

def bd_as_int(p):
	if not "born" in p:
		return 366 * 10000

	def d_to_int(d, m, y):
		return int(d) + 31 * int(m) + 366 * int(y)

	s = p["born"].split('.')
	if len(s) == 1:
		return d_to_int(0, 6, s[0])
	if len(s) == 2:
		return d_to_int(15, s[0], s[1])
	return d_to_int(s[0], s[1], s[2])

def show_leveled(tree):
	print("<html><head>")
	print("</head><body>")
	print("<table border=0 cellspacing=0 cellpadding=0 align=\"center\">")

	def space(w):
		print(f"<td colspan={w}>&nbsp;</\td>")

	def maybe_space(off, o):
		if off < o:
			space(o - off)
			return o
		else:
			return off

	def parent_off(n):
		o = n["_off"]
		w = n["_width"]
		l = len(n["people"])
		if w >= l:
			o += int((w - l)/2)
		for p in sorted(n["people"], key=bd_as_int):
			if p["_grafted"]:
				o += 1
			else:
				break
		return o

	def show_p(p, off, w):
		n = p.get("name", "?")
		print("<td align=\"center\">")
		if not p["_grafted"]:
			img = p.get("img", "img/no-photo.svg")
			ln = ''
			if not "father" in p:
				ln = lastname_str(p, "<br><i>", "</i>")
			print(f"<img src=\"{img}\"/><br>{n}{ln}")
		else:
			img = p.get("img", "img/no-photo-small.svg")
			print(f"<img src=\"{img}\"/><br><small>{n}</small>")
		print("</td>")

	def show_missed_siblings(ppl):
		if len(ppl) > 4:
			print(f"<td align=\"center\" valign=\"bottom\">+{len(ppl)}</td>")
		else:
			print("<td align=\"center\" valign=\"bottom\">")
			for p in ppl:
				n = p.get("name", "?")
				print(f"{n}<br>")
			print("</td>")

	def show_nodes(nodes, width):
		nxt = []
		off = 0
		infos = []
		c_links = []
		p_links = []
		grp = 0
		print("<tr>")
		for node in nodes:
			ppl = sorted(node["people"], key=bd_as_int)
			w = node["_width"]
			l = len(ppl)

			o = node["_off"]
			off = maybe_space(off, o)

			def l_type(i, n):
				if n == 1:
					return 'single'
				elif i == 0:
					return 'first'
				elif i == n - 1:
					return 'last'
				else:
					return 'next'

			if l > w:
				# more people than available width
				# print grafted as list
				# skip step-siblings
				miss = []
				pi = 0
				for p in ppl:
					if not p["_grafted"]:
						if "father" in node or "mother" in node:
							c_links.append({"off": off, "t": l_type(pi, l)})
						show_p(p, off, w)
						infos.append({"off": off, "p": p})
						off += 1
						pi += 1
					else:
						miss.append(p)

				if w >= 2 and miss:
					show_missed_siblings(miss)
					c_links.append({"off": off, "t": l_type(l - 1, l)})
					off += 1

			else:
				# have space for everyone
				# try to fit step-siblings as well
				sp = w - l
				sp_b = int(sp / 2)
				sp_a = sp - sp_b

				o += sp_b

				def own_kids(n, d):
					if d in n:
						fp = n[d]
						if "own_kids" in fp:
							return sorted(fp["own_kids"]["people"], key=bd_as_int)
					return None

				def show_step_siblings(ppl, sp, off):
					xl = len(ppl)
					if xl <= sp:
						off = maybe_space(off, o - xl)
						pi = 0
						for p in ppl:
							show_p(p, off, w)
							c_links.append({"off": off, "t": l_type(pi, xl)})
							off += 1
							pi += 1
					elif sp >= 1:
						show_missed_siblings(ppl)
						c_links.append({"off": off, "t": "single"})
						off += 1

					return off

				x_ppl = own_kids(node, "father")
				if x_ppl:
					off = show_step_siblings(x_ppl, sp_b, off)

				off = maybe_space(off, o)

				pi = 0
				for p in ppl:
					if "father" in node or "mother" in node:
						c_links.append({"off": off, "t": l_type(pi, l)})
					show_p(p, off, w)
					infos.append({"off": off, "p": p})
					off += 1
					pi += 1

				x_ppl = own_kids(node, "mother")
				if x_ppl:
					off = show_step_siblings(x_ppl, sp_a, off)

			grp += 1

			if "father" in node:
				fn = node["father"]
				po = parent_off(fn)
				lt = "single"
				if "mother" in node:
					lt = "father"
				p_links.append({"off": po, "t": lt, "up": o})
				nxt.append(fn)
			if "mother" in node:
				mn = node["mother"]
				po = parent_off(mn)
				p_links.append({"off": po, "t": "mother"})
				nxt.append(mn)

		off = maybe_space(off, width)
		print("</tr>")

		print("<tr>")
		off = 0
		for i in infos:
			off = maybe_space(off, i["off"])
			p = i["p"]
			bd = p.get("born", None)
			dd = p.get("died", None)
			plc = p.get("places", [])
			print("<td align=\"center\"><small>")
			if bd:
				if dd:
					print(f"{bd}<br>{dd}")
				else:
					print(f"{bd}")

			if plc:
				p = plc[0].split()[0]
				print(f"<br>{p}")
			print("</small></td>")
			off += 1

		print("</tr>")

		if nxt:
			print("</tr>")
			print("<tr>")
			off = 0
			for l in c_links:
				off = maybe_space(off, l["off"])
				t = l["t"]
				print(f"<td><img src=\"img/conn-{t}.svg\"/></td>")
				off += 1
			off = maybe_space(off, width)
			print("</tr>")

			print("<tr>")
			off = 0
			skip = False
			skip_up = None
			for l in p_links:
				if not skip:
					off = maybe_space(off, l["off"])
				else:
					while off < l["off"]:
						if off == skip_up:
							print("<td><img src=\"img/conn-skip-up.svg\"/></td>")
						else:
							print("<td><img src=\"img/conn-skip.svg\"/></td>")
						off += 1
					skip = False
				t = l["t"]
				if t == "father":
					skip = True
					skip_up = l["up"]
					if skip_up == off:
						t = "father-up"

				print(f"<td><img src=\"img/conn-{t}.svg\"/></td>")
				off += 1

			off = maybe_space(off, width)

			show_nodes(nxt, width)

	show_nodes([tree], tree["_width"])

	print("</table>")
	print("</body></html>")

show_leveled(tree)
