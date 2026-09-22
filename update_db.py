import sqlite3

conn = sqlite3.connect("database.db")
db = conn.cursor()

ipc_data = [

    ("120B", "Criminal conspiracy"),
    ("141", "Unlawful assembly"),
    ("147", "Rioting"),
    ("149", "Every member of unlawful assembly guilty of offence"),
    ("323", "Voluntarily causing hurt"),
    ("324", "Causing hurt by dangerous weapons"),
    ("326", "Grievous hurt by dangerous weapons"),
    ("354", "Assault on woman"),
    ("363", "Kidnapping"),
    ("376", "Rape"),
    ("379", "Theft"),
    ("403", "Dishonest misappropriation of property"),
    ("406", "Criminal breach of trust"),
    ("409", "Criminal breach of trust by public servant"),
    ("420", "Cheating and dishonestly inducing delivery of property"),
    ("463", "Forgery"),
    ("468", "Forgery for purpose of cheating"),
    ("471", "Using forged document"),
    ("499", "Defamation"),
    ("504", "Intentional insult provoking breach of peace"),
    ("506", "Criminal intimidation"),
    ("509", "Word or gesture insulting modesty of woman"),
    ("441", "Criminal trespass"),
    ("442", "House-trespass"),  
    ("443", "Lurking house-trespass"),
    ("444", "Night trespass"),  
    ("445", "House-breaking"),
    ("446", "House-breaking by night"),
    ("447", "Lurking house-breaking"),
    ("448", "Lurking house-breaking by night"),
    ("506", "Criminal intimidation"),
    ("509", "Word or gesture insulting modesty of woman"),
    ("511", "Attempt to commit an offence punishable with imprisonment for life or other imprisonment"),
    ("120B", "Criminal conspiracy"),
    ("141", "Unlawful assembly"),
    ("147", "Rioting"),
    ("149", "Every member of unlawful assembly guilty of offence"),
    ("323", "Voluntarily causing hurt"),
    ("324", "Causing hurt by dangerous weapons"),
    ("326", "Grievous hurt by dangerous weapons"),
    ("354", "Assault on woman"),
    ("363", "Kidnapping"),
    ("376", "Rape"),
    ("379", "Theft"),
    ("403", "Dishonest misappropriation of property"),
    ("406", "Criminal breach of trust"),
    ("409", "Criminal breach of trust by public servant"),
    ("420", "Cheating and dishonestly inducing delivery of property"),
    ("463", "Forgery"),
    ("468", "Forgery for purpose of cheating"),
    ("471", "Using forged document"),
    ("499", "Defamation"),
    ("504", "Intentional insult provoking breach of peace"),
    ("506", "Criminal intimidation"),
    ("509", "Word or gesture insulting modesty of woman"),
    ("441", "Criminal trespass"),   
    ("442", "House-trespass"),  
    ("443", "Lurking house-trespass"),
    ("444", "Night trespass"),  
    ("445", "House-breaking"),
    ("446", "House-breaking by night"),
    ("447", "Lurking house-breaking"),
    ("448", "Lurking house-breaking by night"),
    ("506", "Criminal intimidation"),
    ("509", "Word or gesture insulting modesty of woman"),
    ("511", "Attempt to commit an offence punishable with imprisonment for life or other imprisonment"),
    ("120B", "Criminal conspiracy"),
    ("141", "Unlawful assembly"),
    ("147", "Rioting"),
    ("149", "Every member of unlawful assembly guilty of offence"),
    ("323", "Voluntarily causing hurt"),
    ("324", "Causing hurt by dangerous weapons"),
    ("326", "Grievous hurt by dangerous weapons"),
    ("354", "Assault on woman"),
    ("363", "Kidnapping"),
    ("376", "Rape"),
    ("379", "Theft"),
    ("403", "Dishonest misappropriation of property"),
    ("406", "Criminal breach of trust"),
    ("409", "Criminal breach of trust by public servant"),
    ("420", "Cheating and dishonestly inducing delivery of property"),
    ("463", "Forgery"),
    ("468", "Forgery for purpose of cheating"),
    ("471", "Using forged document"),
    ("499", "Defamation"),
    ("504", "Intentional insult provoking breach of peace"),
    ("506", "Criminal intimidation"),
    ("509", "Word or gesture insulting modesty of woman"),
    ("441", "Criminal trespass"),   
    ("442", "House-trespass"),  
    ("443", "Lurking house-trespass"),
    ("444", "Night trespass"),  
    ("445", "House-breaking"),
    ("446", "House-breaking by night"),
    ("447", "Lurking house-breaking"),
    ("448", "Lurking house-breaking by night"),
    ("506", "Criminal intimidation"),
    ("509", "Word or gesture insulting modesty of woman"),
    ("511", "Attempt to commit an offence punishable with imprisonment for life or other imprisonment")
     
    


]

for code, title in ipc_data:

    try:
        db.execute("""
        INSERT INTO ipc_sections (section_code, section_title)
        VALUES (?, ?)
        """, (code, title))

    except:
        pass

conn.commit()

print("IPC sections added successfully!")

conn.close()