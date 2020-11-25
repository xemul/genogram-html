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

def gender(p):
	if "name" not in p:
		return "p"
	if p["name"].endswith('а'):
		return "f"
	else:
		return "m"

def lastname_str(p):
	if not p["_family"]:
		return "?"
	br = p["_family"]
	return br[gender(p)]

def full_name_str(p):
	name = p.get("name", "?")
	pname = p.get("patronymic", "")
	lname = lastname_str(p)
	return f"{lname} {name} {pname}"


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


def show_leveled(tree):
	levels = []
	lst = [ tree ]
	while lst:
		cnt = 0
		nxt = []
		cur = []
		for t in lst:
			cnt += len(t["people"])
			if "father" in t:
				ft = t["father"]
				nxt.append(ft)
				if "own_kids" in ft:
					ok = ft["own_kids"]
					cnt += len(ok["people"])
					cur.append(ok)
			cur.append(t)
			if "mother" in t:
				mt = t["mother"]
				nxt.append(mt)
				if "own_kids" in mt:
					ok = mt["own_kids"]
					cnt += len(ok["people"])
					cur.append(ok)

		levels.append({"len": cnt, "g": cur, "set": False})
		lst = nxt


	def find_longest(lst):
		cnt = 0
		lidx = -1
		idx = 0

		for l in lst:
			if not l["set"]:
				if l["len"] > cnt:
					cnt = l["len"]
					lidx = idx
			idx += 1

		return lidx


	def do_straight_offsets(lvl, maxl):
		off = int((maxl - lvl["len"]) / 2)
		for t in lvl["g"]:
			for p in t["people"]:
				p["_off"] = off
				off += 1

		lvl["offsets"] = "S"

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


	def do_parent_offsets(lvl):
		off = 0
		for t in lvl["g"]:
			first = False
			for p in sorted(t["people"], key=bd_as_int):
				if not first:
					n = p.get("name", "?")
					foff = 0
					if p["_father"]:
						foff = p["_father"]["_off"]
						if p["_mother"]:
							moff = p["_mother"]["_off"]
							gap = moff - foff
							foff += int(gap/2)
							foff -= int((len(t["people"])-1)/2)
						elif t.get("side", False):
							foff -= len(t["people"])
					elif p["_mother"]:
						foff = p["_mother"]["_off"]

					if foff > off:
						off = foff
					first = True

				p["_off"] = off
				off += 1

		lvl["offsets"] = "P"


	def do_child_offsets(lvl):
		off = 0
		for t in lvl["g"]:
			for p in t["people"]:
				n = p.get("name", "?")
				coff = p["_kids"][0]["_off"]
				if coff > off:
					off = coff

				p["_off"] = off
				off += 1

		lvl["offsets"] = "C"
				

	maxl = None
	while True:
		i = find_longest(levels)
		if i == -1:
			break
		if not maxl:
			maxl = levels[i]["len"]

		levels[i]["set"] = True
		if i < len(levels) - 1 and levels[i + 1]["set"]:
			do_parent_offsets(levels[i])
			continue

		if i > 0 and levels[i - 1]["set"]:
			do_child_offsets(levels[i])
			continue

		do_straight_offsets(levels[i], maxl)

	print("<html><head>")
	print("</head><body>")
	print("<table border=0 cellspacing=0 cellpadding=0 align=\"center\">")

	def fill_line(l, fill, gap, ctx):
		print("<tr>")
		cnt = l["len"]
		#print(f"<td><small>{cnt}/{ot}</small></td>")
		loff = 0
		for t in l["g"]:
			pi = 0
			for p in sorted(t["people"], key=bd_as_int):
				off = p.get("_off", -1)
				if loff < off:
					if ctx:
						while loff < off:
							print("<td>")
							gap(ctx)
							print("</td>")
							loff += 1
					else:
						print(f"<td colspan={off - loff}>")
						gap(ctx)
						print("</td>")
						loff = off

				print("<td align=\"center\" valign=\"middle\">")
				fill(p, pi, len(t["people"]), cnt, ctx)
				print("</td>")
				loff += 1
				pi += 1

		if loff < maxl:
			print(f"<td colspan={maxl - loff}>")
			gap(ctx)
			print("</td>")
			loff = off

		print("</tr>")

	def fill_person(p, pi, pn, cnt, ctx):
		n = p.get("name", "?")
		img = p.get("img", "img/no-photo.svg")
		print(f"<img src=\"{img}\"/><br>")
		if cnt > 16 or p["_grafted"]:
			print("<small>")
		print(f"{n}")
		if cnt > 16 or p["_grafted"]:
			print("</small>")

	def fill_person_data(p, pi, pn, cnt, ctx):
		bd = p.get("born", None)
		dd = p.get("died", None)
		if bd:
			print("<small>")
			if dd:
				print(f"{bd}&ndash;{dd}")
			else:
				print(f"{bd}")
			print("</small>")

	def fill_conn(t):
		print(f"<img src=\"img/conn-{t}.svg\"/>")

	def fill_gap(ctx):
		print("&nbsp;")

	def fill_kid_connectors(p, pi, pn, cnt, ctx):
		if p["_father"] or p["_mother"]:
			if pn == 1:
				fill_conn('single')
			elif pi == 0:
				fill_conn('first')
			elif pi == pn - 1:
				fill_conn('last')
			else:
				fill_conn('next')
		else:
			print("&nbsp;")

	def fill_parent_connectors(p, pi, pn, cnt, ctx):
		if p["_wife"]:
			fill_conn('father')
			ctx["start"] = True
		elif p["_husband"]:
			fill_conn('mother')
			ctx["start"] = False
		elif ctx["start"]:
			fill_conn('skip')
		elif not p["_grafted"]:
			fill_conn('single')
		else:
			print("&nbsp;")

	def fill_parent_gap(ctx):
		if ctx["start"]:
			fill_conn('skip')
		else:
			fill_gap(ctx)

	for l in levels:
		if not l == levels[0]:
			pc_ctx = {"start": False}
			fill_line(l, fill_parent_connectors, fill_parent_gap, pc_ctx)

		fill_line(l, fill_person, fill_gap, None)
		fill_line(l, fill_person_data, fill_gap, None)

		if not l == levels[-1]:
			fill_line(l, fill_kid_connectors, fill_gap, None)

	print("</table>")
	print("</body></html>")

show_leveled(tree)
