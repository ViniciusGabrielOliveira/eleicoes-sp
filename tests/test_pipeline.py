import csv
import hashlib
import io
import json
import zipfile

import duckdb
import pytest

from eleicoes_sp import pipeline
from eleicoes_sp.download import SOURCES

def archive(root,key,tables):
    folder=root/"data/raw"/key
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/SOURCES[key][1]
    with zipfile.ZipFile(path,"w") as z:
        for name,records in tables.items():
            stream=io.StringIO()
            writer=csv.DictWriter(stream,fieldnames=records[0],delimiter=";")
            writer.writeheader();writer.writerows(records)
            z.writestr(name,stream.getvalue().encode("latin1"))
    (folder/"source.json").write_text(json.dumps({"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}))

def test_complete_import_and_failed_refresh_preserves_snapshot(tmp_path,monkeypatch):
    root=tmp_path
    (root/"reports").mkdir()
    monkeypatch.setattr(pipeline,"ROOT",root)
    monkeypatch.setattr(pipeline,"RAW",root/"data/raw")
    monkeypatch.setattr(pipeline,"WAREHOUSE",root/"data/warehouse")
    monkeypatch.setattr(pipeline,"DATABASE",root/"data/warehouse/eleicoes.duckdb")
    def vote(office,election,number,candidate,votes,uf="SP"):
        return dict(ANO_ELEICAO=2026,CD_ELEICAO=election,NR_TURNO=1,SG_UF=uf,
            CD_MUNICIPIO=71072,NM_MUNICIPIO="SÃO PAULO",NR_ZONA=1,NR_SECAO=1,
            CD_CARGO=office,DS_CARGO=str(office),NR_VOTAVEL=number,NM_VOTAVEL=str(candidate),
            QT_VOTOS=votes,NR_LOCAL_VOTACAO=100,SQ_CANDIDATO=candidate,
            NM_LOCAL_VOTACAO="ESCOLA",DS_LOCAL_VOTACAO_ENDERECO="RUA A, 1")
    archive(root,"votes_sp",{"votacao_secao_2026_SP.csv":[vote(6,6259,1010,100,30),
        vote(6,6259,2020,200,70),vote(6,6259,95,-1,20),vote(6,6259,10,-1,40)]})
    archive(root,"votes_br",{"votacao_secao_2026_BR.csv":[vote(1,6257,10,300,50),
        vote(1,6257,20,400,80),vote(1,6257,95,-1,30),vote(1,6257,10,300,100,"RS")]})
    archive(root,"locations",{"eleitorado_local_votacao_2026_SP.csv":[dict(
        AA_ELEICAO=2026,NR_TURNO=1,SG_UF="SP",CD_MUNICIPIO=71072,NR_ZONA=1,
        NR_LOCAL_VOTACAO=100,NM_LOCAL_VOTACAO="ESCOLA",DS_ENDERECO="RUA A, 1",
        NM_BAIRRO="CENTRO",NR_CEP="01000000",NR_LATITUDE="-23,5",NR_LONGITUDE="-46,6")]})
    def candidate(office,election,id,number,uf):
        return dict(ANO_ELEICAO=2026,CD_ELEICAO=election,NR_TURNO=1,SQ_CANDIDATO=id,
            CD_CARGO=office,NR_CANDIDATO=number,NM_CANDIDATO=str(id),NM_URNA_CANDIDATO=str(id),
            SG_PARTIDO="AAA",DS_SITUACAO_CANDIDATURA="APTO",DS_SIT_TOT_TURNO="ELEITO",SG_UF=uf)
    archive(root,"candidates",{"consulta_cand_2026_SP.csv":[candidate(6,6259,100,1010,"SP"),
        candidate(6,6259,200,2020,"SP")],"consulta_cand_2026_BR.csv":[candidate(1,6257,300,10,"BR"),
        candidate(1,6257,400,20,"BR")]})
    def turnout(office,election,nominal,party):
        return dict(ANO_ELEICAO=2026,CD_ELEICAO=election,NR_TURNO=1,SG_UF="SP",
            CD_MUNICIPIO=71072,NR_ZONA=1,NR_SECAO=1,CD_CARGO=office,QT_APTOS=200,
            QT_COMPARECIMENTO=160,QT_ABSTENCOES=40,QT_VOTOS_NOMINAIS=nominal,
            QT_VOTOS_BRANCOS=160-nominal-party,QT_VOTOS_NULOS=0,QT_VOTOS_LEGENDA=party,
            QT_VOTOS_ANULADOS_APU_SEP=0)
    def write_turnout(nominal):
        archive(root,"turnout",{"detalhe_votacao_secao_2026_SP.csv":[turnout(6,6259,nominal,40)],
            "detalhe_votacao_secao_2026_BR.csv":[turnout(1,6257,130,0)]})
    write_turnout(100)
    pipeline.build()
    with duckdb.connect(str(pipeline.DATABASE),read_only=True) as con:
        assert con.execute("SELECT count(*),sum(votes) FROM votes").fetchone()==(7,320)
        assert con.execute("SELECT count(*) FROM sections WHERE neighborhood='CENTRO'").fetchone()[0]==2
        assert con.execute("SELECT count(*) FROM summary_section").fetchone()[0]==4
    original=pipeline.DATABASE.read_bytes()
    write_turnout(99)
    with pytest.raises(ValueError,match="totalização oficial"):
        pipeline.build()
    assert pipeline.DATABASE.read_bytes()==original
