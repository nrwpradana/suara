import json
import requests
import pandas as pd
import numpy as np
import streamlit as st

def compare(id,tingkat):
    #get data from api kawalpemilu.org
    
    if tingkat == 'desa':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id="+str(id)).json()
    elif tingkat == 'kec':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id="+str(id)[0:6]).json()
    elif tingkat == 'kab':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id="+str(id)[0:4]).json()
    elif tingkat == 'prov':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id="+str(id)[0:2]).json()
    elif tingkat == 'nas':
        data = requests.get("https://kp24-fd486.et.r.appspot.com/h?id=").json()

    aggregated_data = data["result"]["aggregated"]

    dfs = []
    for key, values in aggregated_data.items():
        df = pd.DataFrame(values)
        dfs.append(df)

    df = pd.concat(dfs,ignore_index=True)

    if tingkat == 'desa':
        df = df[['idLokasi', 'pas1', 'pas2', 'pas3', 'dpt', 'name']].drop_duplicates(subset=['idLokasi'],keep='first')
    else: 
        df = df[['idLokasi', 'pas1', 'pas2', 'pas3', 'totalTps', 'name']].drop_duplicates(subset=['idLokasi'],keep='first')
    df['status'] = np.where((df['pas1'] == 0) & (df['pas2'] == 0) & (df['pas3'] == 0), 0, 1)
    if tingkat == 'desa':
        df['idLokasi'] = id*1000 + df['name'].astype(int)
    df['idLokasi'] = df['idLokasi'].astype(str)
    kawalpemilu = df

    #get data from api sirekap kpu
    if tingkat == 'desa':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/"+str(id)[0:2]+"/"+str(id)[0:4]+"/"+str(id)[0:6]+"/"+str(id)+".json").json()
    elif tingkat == 'kec':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/"+str(id)[0:2]+"/"+str(id)[0:4]+"/"+str(id)[0:6]+".json").json()
    elif tingkat == 'kab':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/"+str(id)[0:2]+"/"+str(id)[0:4]+".json").json()
    elif tingkat == 'prov':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp/"+str(id)[0:2]+".json").json()
    elif tingkat == 'nas':
        data = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp.json").json()

    rows = []

    for id_, values in data['table'].items():
        row = {
            'id': id_,
            'psu': values['psu'],
            'persen': values['persen'],
            'status_progress': values['status_progress']
        }

        if '100025' in values:
            row['100025'] = int(values['100025'])
        else: row['100025'] = 0
        if '100026' in values:
            row['100026'] = int(values['100026'])
        else: row['100026'] = 0  
        if '100027' in values:
            row['100027'] = int(values['100027'])
        else: row['100027'] = 0
        rows.append(row)

    df = pd.DataFrame(rows)

    df['id'] = df['id'].astype(str)
    df = df.rename(columns={'100025':'pas1','100026':'pas2','100027':'pas3'})
    df = df[['id','pas1','pas2','pas3']].fillna(0)
    df['pas1'] = df['pas1'].astype(int)
    df['pas2'] = df['pas2'].astype(int)
    df['pas3'] = df['pas3'].astype(int)
    df['status'] = np.where((df['pas1'] == 0) & (df['pas2'] == 0) & (df['pas3'] == 0), 0, 1)
    kpu = df

    if tingkat == 'desa':
        #merge data sirekap kpu with kawalpemilu.org
        compared = pd.merge(kawalpemilu, kpu, left_on='idLokasi', right_on='id', how='inner')
        compared.columns = ['idLokasi', 'pas1_kawal', 'pas2_kawal', 'pas3_kawal', 'dpt', 'name', 'status_kawal',
               'id', 'pas1_kpu', 'pas2_kpu', 'pas3_kpu', 'status_kpu']
        compared = compared[['id','dpt','pas1_kawal', 'pas2_kawal', 'pas3_kawal','status_kawal','pas1_kpu', 'pas2_kpu', 'pas3_kpu', 'status_kpu']]

        #compare sirekap kpu with kawalpemilu.org
        def check(row):
            if row['status_kawal'] == 1 and row['status_kpu'] == 1:
                if row['pas1_kawal'] == row['pas1_kpu'] and row['pas2_kawal'] == row['pas2_kpu'] and row['pas3_kawal'] == row['pas3_kpu']:
                    return 'sesuai' #detect ketidaksesuaian dengan kawalpemilu
                elif row['pas1_kpu'] + row['pas2_kpu'] + row['pas3_kpu'] > row['dpt']*1.02 or row['pas1_kawal'] + row['pas2_kawal'] + row['pas3_kawal'] > row['dpt']*1.02:
                    return 'markup' #detect markup suara
                else: return 'tidak sesuai' #detect ketidaksesuaian dengan kawalpemilu
            elif row['pas1_kpu'] + row['pas2_kpu'] + row['pas3_kpu'] > row['dpt']*1.02 or row['pas1_kawal'] + row['pas2_kawal'] + row['pas3_kawal'] > row['dpt']*1.02:
                return 'markup' #detect markup suara
            else: 
                return 'belum dikawal' #detect tps belum dikawal/data belum ada di kawalpemilu
        compared['check'] = compared.apply(check, axis=1)
    else:
        #merge data sirekap kpu with kawalpemilu.org
        compared = pd.merge(kawalpemilu, kpu, left_on='idLokasi', right_on='id', how='inner')
        compared.columns = ['idLokasi', 'pas1_kawal', 'pas2_kawal', 'pas3_kawal', 'totalTps', 'name', 'status_kawal',
               'id', 'pas1_kpu', 'pas2_kpu', 'pas3_kpu', 'status_kpu']
        compared = compared[['name','totalTps','pas1_kawal', 'pas2_kawal', 'pas3_kawal','status_kawal','pas1_kpu', 'pas2_kpu', 'pas3_kpu', 'status_kpu']]

        #compare sirekap kpu with kawalpemilu.org
        def check(row):
            if row['status_kawal'] == 1 and row['status_kpu'] == 1:
                if row['pas1_kawal'] == row['pas1_kpu'] and row['pas2_kawal'] == row['pas2_kpu'] and row['pas3_kawal'] == row['pas3_kpu']:
                    return 'sesuai' #detect ketidaksesuaian dengan kawalpemilu
                else: return 'tidak sesuai' #detect ketidaksesuaian dengan kawalpemilu
            else: 
                return 'belum dikawal' #detect tps belum dikawal/data belum ada di kawalpemilu
        compared['check'] = compared.apply(check, axis=1)
    return compared

# Fungsi untuk menambahkan warna baris berdasarkan kondisi
def row_color(row):
    color = '#8DE3D1' if row['check'] == 'sesuai' else '#EC7063' if row['check'] == 'markup' or row['check'] == 'tidak sesuai' else '#e3e3e3'
    return [f'background-color: {color}'] * len(row)

tps = pd.read_json("tps.json",dtype=False)

st.set_page_config(layout="wide")

tab1, tab2 = st.tabs(["Suara Paslon","Suara Per Wilayah"])

with tab2:
    st.header("Sirekap KPU vs KawalPemilu.org")

    d1, d2, d3 = st.columns(3)

    #Dropdown options PROVINSI
    opsi_prov = tps[tps.index.astype(str).str.len() == 2]['id2name']
    nm_prov = d1.selectbox('Pilih Provinsi:', opsi_prov, key='d_prov')
    id_prov = tps[(tps.index.astype(str).str.len() == 2) & (tps['id2name'] == nm_prov)].index[0]

    #Dropdown options KABUPATEN/KOTA
    opsi_kab = tps[(tps.index.astype(str).str.len() == 4) & (tps.index.astype(str).str.startswith(str(id_prov)))]['id2name']
    nm_kab = d2.selectbox('Pilih Kabupaten/Kota:', opsi_kab, key='d_kab')
    id_kab = tps[(tps.index.astype(str).str.len() == 4) & (tps.index.astype(str).str.startswith(str(id_prov))) & (tps['id2name'] == nm_kab)].index[0]

    #Dropdown options KECAMATAN
    opsi_kec = tps[(tps.index.astype(str).str.len() == 6) & (tps.index.astype(str).str.startswith(str(id_kab)))]['id2name']
    nm_kec = d3.selectbox('Pilih Kecamatan:', opsi_kec, key='d_kec')
    id_kec = tps[(tps.index.astype(str).str.len() == 6) & (tps.index.astype(str).str.startswith(str(id_kab))) & (tps['id2name'] == nm_kec)].index[0]

    id_wil = id_kec

    tab_nasional, tab_provinsi, tab_kabkot, tab_kecamatan = st.tabs(['Nasional','Provinsi','Kab/Kota','Kecamatan'])

    with tab_nasional:
        st.subheader('Suara Nasional')
        w1, w2, w3 = st.columns([1,1,6])
        w1.link_button("🗳️ SIREKAP KPU", "https://pemilu2024.kpu.go.id/pilpres/hitung-suara/",use_container_width = True)
        w2.link_button("🔢 KAWAL PEMILU", "https://kawalpemilu.org/h/",use_container_width = True)
        w3.write(f"""<b>  NASIONAL</b>
                 """, unsafe_allow_html=True)
        id = int(id_wil)
        # Menampilkan dataframe
        df = compare(id_wil, tingkat = 'nas')
        st.dataframe(df.style.apply(row_color, axis=1),use_container_width = True)
        #Menampilkan diagram batang
        st.subheader('Diagram Suara:')
        w4, w5 = st.columns(2)
        w4.subheader('🔢 Kawal Pemilu')
        w4.bar_chart(df[['name','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'name': 'provinsi'}), 
                     x='provinsi',
                     color=['#CCFFCC','#CCCCFF','#FFCCCC'])
        w5.subheader('🗳️ Sirekap KPU')
        w5.bar_chart(df[['name','pas1_kpu','pas2_kpu','pas3_kpu']].rename(columns={'name': 'provinsi'}), 
                     x='provinsi', 
                     color=['#CCFFCC','#CCCCFF','#FFCCCC'])

    with tab_provinsi:
        st.subheader('Suara Provinsi:')
        x1, x2, x3 = st.columns([1,1,6])
        x1.link_button("🗳️ SIREKAP KPU", "https://pemilu2024.kpu.go.id/pilpres/hitung-suara/"+str(id_wil)[0:2],use_container_width = True)
        x2.link_button("🔢 KAWAL PEMILU", "https://kawalpemilu.org/h/"+str(id_wil)[0:2],use_container_width = True)
        x3.write(f"""<b>  PROVINSI:</b> {tps.loc[int(str(id_wil)[0:2]),'id2name']}
                 """, unsafe_allow_html=True)
        id = int(id_wil)
        # Menampilkan dataframe
        df = compare(id_wil, tingkat = 'prov')
        st.dataframe(df.style.apply(row_color, axis=1),use_container_width = True)
        #Menampilkan diagram batang
        st.subheader('Diagram Suara:')
        x4, x5 = st.columns(2)
        x4.subheader('🔢 Kawal Pemilu')
        x4.bar_chart(df[['name','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'name': 'kabupaten_kota'}), 
                     x='kabupaten_kota',
                     color=['#CCFFCC','#CCCCFF','#FFCCCC'])
        x5.subheader('🗳️ Sirekap KPU')
        x5.bar_chart(df[['name','pas1_kpu','pas2_kpu','pas3_kpu']].rename(columns={'name': 'kabupaten_kota'}), 
                     x='kabupaten_kota', 
                     color=['#CCFFCC','#CCCCFF','#FFCCCC'])

    with tab_kabkot:
        st.subheader('Suara Kab/Kota:')
        y1, y2, y3 = st.columns([1,1,6])
        y1.link_button("🗳️ SIREKAP KPU", "https://pemilu2024.kpu.go.id/pilpres/hitung-suara/"+str(id_wil)[0:2]+"/"+str(id_wil)[0:4],use_container_width = True)
        y2.link_button("🔢 KAWAL PEMILU", "https://kawalpemilu.org/h/"+str(id_wil)[0:4],use_container_width = True)
        y3.write(f"""<b>  PROVINSI:</b> {tps.loc[int(str(id_wil)[0:2]),'id2name']} | 
                 <b>  KAB/KOTA:</b> {tps.loc[int(str(id_wil)[0:4]),'id2name']}
                 """, unsafe_allow_html=True)
        id = int(id_wil)
        # Menampilkan dataframe
        df = compare(id_wil, tingkat = 'kab')
        st.dataframe(df.style.apply(row_color, axis=1),use_container_width = True)
        #Menampilkan diagram batang
        st.subheader('Diagram Suara:')
        y4, y5 = st.columns(2)
        y4.subheader('🔢 Kawal Pemilu')
        y4.bar_chart(df[['name','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'name': 'kecamatan'}), 
                     x='kecamatan',
                     color=['#CCFFCC','#CCCCFF','#FFCCCC'])
        y5.subheader('🗳️ Sirekap KPU')
        y5.bar_chart(df[['name','pas1_kpu','pas2_kpu','pas3_kpu']].rename(columns={'name': 'kecamatan'}), 
                     x='kecamatan', 
                     color=['#CCFFCC','#CCCCFF','#FFCCCC'])

    with tab_kecamatan:
        st.subheader('Suara Kecamatan:')
        z1, z2, z3 = st.columns([1,1,6])
        z1.link_button("🗳️ SIREKAP KPU", "https://pemilu2024.kpu.go.id/pilpres/hitung-suara/"+str(id_wil)[0:2]+"/"+str(id_wil)[0:4]+"/"+str(id_wil),use_container_width = True)
        z2.link_button("🔢 KAWAL PEMILU", "https://kawalpemilu.org/h/"+str(id)[0:6],use_container_width = True)
        z3.write(f"""<b>  PROVINSI:</b> {tps.loc[int(str(id_wil)[0:2]),'id2name']} | 
                 <b>  KAB/KOTA:</b> {tps.loc[int(str(id_wil)[0:4]),'id2name']} |
                 <b>  KECAMATAN:</b> {tps.loc[int(str(id_wil)),'id2name']}
                 """, unsafe_allow_html=True)
        id = int(id_wil)
        # Menampilkan dataframe
        df = compare(id_wil, tingkat = 'kec')
        st.dataframe(df.style.apply(row_color, axis=1),use_container_width = True)
        #Menampilkan diagram batang
        st.subheader('Diagram Suara:')
        z4, z5 = st.columns(2)
        z4.subheader('🔢 Kawal Pemilu')
        z4.bar_chart(df[['name','pas1_kawal','pas2_kawal','pas3_kawal']].rename(columns={'name': 'desa_kelurahan'}), 
                     x='desa_kelurahan',
                     color=['#CCFFCC','#CCCCFF','#FFCCCC'])
        z5.subheader('🗳️ Sirekap KPU')
        z5.bar_chart(df[['name','pas1_kpu','pas2_kpu','pas3_kpu']].rename(columns={'name': 'desa_kelurahan'}), 
                     x='desa_kelurahan', 
                     color=['#CCFFCC','#CCCCFF','#FFCCCC'])


with tab1:
    st.header("Suara Pasangan (Sirekap vs KawalPemilu)")

    #Rekapitulasi Sirekap KPU
    kpu = requests.get("https://sirekap-obj-data.kpu.go.id/pemilu/hhcw/ppwp.json").json()['chart']
    kpu_pas1 = kpu['100025']
    kpu_pas2 = kpu['100026']
    kpu_pas3 = kpu['100027']
    kpu_tot = kpu['100025'] + kpu['100026'] + kpu['100027']

    #Rekapitulasi Kawal Pemilu
    kawal = requests.get("https://kp24-fd486.et.r.appspot.com/h?id=").json()['result']['aggregated']
    kawal_pas1 = 0
    kawal_pas2 = 0
    kawal_pas3 = 0
    for lokasi in kawal.values():
        for entry in lokasi:
            kawal_pas1 += entry['pas1']
            kawal_pas2 += entry['pas2']
            kawal_pas3 += entry['pas3']
    kawal_tot = kawal_pas1 + kawal_pas2 + kawal_pas3
    
    c8, c9, c10 = st.columns(3)

    with c8:
        st.header("01")
        c8a, c8b = st.columns([4,2])
        c8a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Anies-Muhaimin.png", use_column_width=True)
        with c8b:
            st.metric(label=":ballot_box_with_ballot: Sirekap KPU", 
                      value=str(round((kpu_pas1/kpu_tot)*100,2))+'%', 
                      delta="{:,}".format(kpu_pas1),
                      delta_color = 'off')
            st.metric(label=":1234: Kawal Pemilu", 
                      value=str(round((kawal_pas1/kawal_tot)*100,2))+'%', 
                      delta="{:,}".format(kawal_pas1),
                      delta_color = 'off')
        #st.subheader("H. ANIES RASYID BASWEDAN, Ph.D. - Dr. (H.C.) H. A. MUHAIMIN ISKANDAR")
        
    
    with c9:
        st.header("02")
        c9a, c9b = st.columns([4,2])
        c9a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Prabowo-Gibran.png", use_column_width=True)
        with c9b:
            st.metric(label=":ballot_box_with_ballot: Sirekap KPU", 
                      value=str(round((kpu_pas2/kpu_tot)*100,2))+'%', 
                      delta="{:,}".format(kpu_pas2),
                      delta_color = 'off')
            st.metric(label=":1234: Kawal Pemilu", 
                      value=str(round((kawal_pas2/kawal_tot)*100,2))+'%', 
                      delta="{:,}".format(kawal_pas2),
                      delta_color = 'off')
        #st.subheader("H. PRABOWO SUBIANTO - GIBRAN RAKABUMING RAKA")
    
    with c10:
        st.header("03")
        c10a, c10b = st.columns([4,2])
        c10a.image("https://asset.kompas.com/data/2023/10/25/kompascom/widget/bacapres/images/paslon/Ganjar-Mahfud.png", use_column_width=True)
        with c10b:
            st.metric(label=":ballot_box_with_ballot: Sirekap KPU", 
                      value=str(round((kpu_pas3/kpu_tot)*100,2))+'%', 
                      delta="{:,}".format(kpu_pas3),
                      delta_color = 'off')
            st.metric(label=":1234: Kawal Pemilu", 
                      value=str(round((kawal_pas3/kawal_tot)*100,2))+'%', 
                      delta="{:,}".format(kawal_pas3),
                      delta_color = 'off')   
        #st.subheader("H. GANJAR PRANOWO, S.H., M.I.P. - Prof. Dr. H. M. MAHFUD MD")
