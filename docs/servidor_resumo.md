# Servidor de produção — resumo da frota (gerado)

> Gerado por `tools/servidor.py resumo` em 03/11/2026 10:38 (BRT), só leitura da API (`https://sighir.com:8000/api/v2`). Não edite: "sincronizar os documentos" refaz. Números mudam todo dia — para uma placa específica use o Helper (`helper.py veiculo PLACA`).

**149 instalações** em 20 empresas · 142 operando · anomalias abertas: 243 · firmware mais novo no catálogo: **v6.4.7** (2026-09-01)

## Por telemetria

| telemetria | instalações |
|---|---|
| Mix Telematics (novo) | 73 |
| Suntech | 46 |
| ? | 15 |
| Mix Telematics | 11 |
| Entrack | 4 |

## Última comunicação (último log recebido)

Na MiX de empresa que não repassa logs, "sem comunicação" pode ser normal (`telemetrias.md`).

| há quanto tempo | instalações |
|---|---|
| < 1 dia | 46 |
| 1–7 dias | 12 |
| 7–30 dias | 31 |
| > 30 dias | 11 |
| nunca | 49 |

## Calibração do sensor (data da calibração corrente, regra de 1 ano)

| situação | instalações |
|---|---|
| vencida (> 365 dias) | 51 |
| vence em ≤ 30 dias | 0 |
| em dia | 85 |
| sem dado | 13 |

## Firmware reportado × catálogo

`software_version` só muda no check-update via Wi-Fi; `1.0.0` = nunca reportou (`portal_app.md` §4).

| versão reportada | instalações |
|---|---|
| 1.0.0 | 60 |
| 6.4.4 | 18 |
| 6.5.0 | 11 |
| 6.4.7 | 9 |
| 6.4.8 | 7 |
| 6.5.1 | 7 |
| 6.3.8 | 5 |
| 6.4.0 | 5 |
| 6.4.5 | 5 |
| 6.3.9 | 3 |
| 6.3.11 | 3 |
| 5.3.7 | 2 |
| 6.3.12 | 2 |
| 6.5.3 | 2 |
| v4.11.6 | 1 |
| v5.1.6 | 1 |
| 1.7.0 | 1 |
| 6.4.6 | 1 |
| v4.11.8 | 1 |
| v4.21.1 | 1 |
| v4.27.7 | 1 |
| 6.4.2 | 1 |
| 6.3.14 | 1 |
| 6.5.2 | 1 |

Catálogo (`firmwares/`, mais novas primeiro):

| versão | data | descrição |
|---|---|---|
| v6.4.7 | 2026-09-01 | melhoria de detecção do sopro; protocolo do etilômetro atualizado e robusto; |
| v6.4.2 | 2026-07-07 | melhorias lingua nova (EN e ES); sensor trocado agora é enviado por telemetria; |
| v6.3.9 | 2026-05-12 | melhorias no modelo de detecção de álcool; telemetria entrack funcional; melhorias na comu |
| v5.3.0 | 2025-05-08 | melhorias na calibração do sensor de álcool; melhorias no sistema de comunicação com telem |
| v5.0.0 | 2025-03-24 | 1) Reestruturação geral de pastas; 2) Melhor organização de itens no menu; 3) Integração d |
| v4.27.0 | 2025-02-10 | 1) atualização de firmware por USB Serial Suntech Concluída; 2) implementação do BLE no Et |
| v4.25.12 | 2025-01-16 | 1) melhorias no sensor de pressão; 2) melhoria da interface do aparelho; 3) implementação  |
| v4.25.12 | 2025-02-07 | 1) atualização de firmware por USB Serial; 2) implementação do BLE no Etilômetro; 3) melho |

## Anomalias abertas (Scanner)

| categoria | abertas |
|---|---|
| calibracao | 80 |
| sem_comunicacao | 36 |
| instalacao_pendente | 34 |
| firmware_desatualizado | 26 |
| falha_integracao | 20 |
| teste_inconclusivo | 14 |
| burla_bloqueio | 12 |
| alcool | 11 |
| dado_corrompido | 3 |
| conduta_motorista | 3 |
| defeito_aparelho | 2 |
| cadastro_inconsistente | 2 |

## Por empresa

| empresa | instalações | telemetrias | sem log ≥ 7 dias | calibração vencida |
|---|---|---|---|---|
| EXPRESSO PREDILETO | 64 | ?, Mix Telematics, Mix Telematics (novo), Suntech | 38 | 23 |
| MOSAIC FERTILIZANTES LTDA | 28 | ?, Mix Telematics, Mix Telematics (novo) | 28 | 10 |
| RICKER TRANSPORTES LTDA | 12 | Suntech | 2 | 2 |
| SIGHIR ENTERPRISE LTDA | 7 | Entrack, Mix Telematics (novo), Suntech | 4 | 2 |
| FAJE LOGISTICA E TRANSPORTE | 7 | Suntech | 1 | 0 |
| LOGIKA TRANSPORTES | 6 | Mix Telematics, Mix Telematics (novo) | 2 | 2 |
| FELKA TRANSPORTES E LOGISTICA | 4 | Mix Telematics, Suntech | 4 | 4 |
| TRANSMAQUINA S.A. | 4 | Suntech | 0 | 0 |
| Klabin S.A | 3 | Suntech | 3 | 2 |
| TRANSPORTES MANCHUR | 2 | Mix Telematics, Mix Telematics (novo) | 2 | 1 |
| BELLA VIA TRANSPORTES LTDA | 2 | Suntech | 2 | 2 |
| ATVOS BIOENERGIA DO PONTAL S.A | 2 | Mix Telematics (novo) | 0 | 0 |
| TRANSPORTES THOMAZ LTDA | 1 | Suntech | 0 | 1 |
| Scania | 1 | Suntech | 1 | 1 |
| Zirix Enterprise | 1 | Suntech | 1 | 1 |
| CONSTRUTORA CENTRO LESTE S/A | 1 | Entrack | 0 | 0 |
| Andrade Telemetria Rastreament | 1 | ? | 1 | 0 |
| DETECTOR LTDA | 1 | Suntech | 1 | 0 |
| TRANSPORTADORA CONTATTO | 1 | Suntech | 1 | 0 |
| Ziran Logística | 1 | Suntech | 0 | 0 |

## Telemetrias cadastradas (`companies/`, type=telemetry)

O `value` é o modo de telemetria gravado no aparelho (`telemetrias.md`).

| telemetria | value | id |
|---|---|---|
| MIX TELEMATICS | 0 | 17131425000132 |
| SUNTECH | 2 | 44922499000 |
| MIX TELEMATICS (NOVO) | 5 | 17131425000130 |
| Entrack | 6 | 12729135000171 |

## Instalações

| placa | empresa | telemetria | tipo | aparelho | firmware | último log | calibração (dias) | operando |
|---|---|---|---|---|---|---|---|---|
| UBR9J42 | ATVOS BIOENERGIA DO PONTAL S.A | Mix Telematics (novo) | caminhão | MIC8391422140241678 | 6.4.0 | 03/11/2026 | 132 | sim |
| UBU2I57 | ATVOS BIOENERGIA DO PONTAL S.A | Mix Telematics (novo) | caminhão | MIC3460577981536923 | 6.4.0 | 02/11/2026 | 132 | sim |
| TESTE ENTRACK | Andrade Telemetria Rastreament | ? | caminhão | MIC8708795299331741 | 6.3.11 | nunca | 192 | sim |
| EOJ5I60 | BELLA VIA TRANSPORTES LTDA | Suntech | caminhão | MIC0990885423811983 | 1.0.0 | nunca | 553 | sim |
| SPX4A02 | BELLA VIA TRANSPORTES LTDA | Suntech | caminhão | MIC5738341846131147 | 1.0.0 | nunca | 538 | sim |
| TFE6H05 | CONSTRUTORA CENTRO LESTE S/A | Entrack | caminhão | MIC8767790427121753 | 6.4.4 | 03/11/2026 | 159 | sim |
| SYM4F89 | DETECTOR LTDA | Suntech | caminhão | MIC0014246467341799 | 1.0.0 | 20/07/2026 | 203 | sim |
| EMP009 | EXPRESSO PREDILETO | ? | caminhão | MIC0483049134592268 | 1.0.0 | 03/11/2025 | 538 | sim |
| EMPRIO | EXPRESSO PREDILETO | Suntech | caminhão | MIC7491597966861498 | 6.3.11 | 03/08/2026 | 173 | sim |
| LUA5E58 | EXPRESSO PREDILETO | Mix Telematics | caminhão | MIC1009016058992021 | 1.0.0 | 06/07/2026 | 68 | sim |
| LUE9A29 | EXPRESSO PREDILETO | Mix Telematics | caminhão | MIC9935714618981987 | 6.3.12 | 30/10/2026 | 284 | não |
| PPQ9017 | EXPRESSO PREDILETO | Mix Telematics | carro | MIC5282201573701056 | 6.5.0 | 03/11/2026 | 123 | sim |
| QRH8I97 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4875498327299753 | 1.0.0 | 03/11/2026 | 532 | sim |
| QRM7G63 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC2654251818395311 | 1.0.0 | 23/10/2026 | ? | sim |
| QRM8G13 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7055839215641411 | 6.3.9 | 16/10/2026 | 271 | sim |
| QRM8G28 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7182391889581436 | 6.3.12 | 15/10/2026 | 235 | não |
| QRM8G34 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8826555221551765 | 1.0.0 | nunca | 538 | sim |
| RJE2J65 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC2948811743345899 | 6.3.11 | 03/11/2026 | 272 | sim |
| RJE6F03 | EXPRESSO PREDILETO | ? | caminhão | MIC3060320331346123 | 6.5.0 | 28/10/2026 | 47 | sim |
| RJG6H37 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC6795935748551359 | 6.3.8 | 21/10/2026 | 188 | sim |
| RJI1C01 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC0155178983031940 | 1.0.0 | 16/10/2026 | 216 | sim |
| RJK1D03 | EXPRESSO PREDILETO | Suntech | caminhão | MIC3474296550936951 | 6.4.4 | 03/11/2026 | 272 | sim |
| RJM4H64 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8443966547941688 | 1.0.0 | nunca | 19 | sim |
| RJN8B5 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9563057659771912 | 6.4.7 | nunca | 537 | sim |
| RJO6I53 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7952031891471590 | 1.0.0 | nunca | ? | sim |
| RJP4I71 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7701672413901540 | 1.0.0 | 16/10/2026 | 536 | sim |
| RJQ3F02 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC1563513907743129 | 6.4.7 | 03/11/2026 | 188 | sim |
| RJR7C09 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9272967618681854 | 1.0.0 | 16/10/2026 | ? | sim |
| RJS5A13 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9558193970261911 | 1.0.0 | 16/10/2026 | 565 | sim |
| RJT5E02 | EXPRESSO PREDILETO | Suntech | caminhão | MIC3004645420106011 | 6.4.8 | 02/11/2026 | 138 | sim |
| RJT8B80 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5283053322081056 | 1.0.0 | 03/11/2026 | ? | sim |
| RJT9G28 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4169182339378341 | 1.0.0 | 02/11/2026 | ? | sim |
| RJV1A55 | EXPRESSO PREDILETO | ? | caminhão | MIC5256069479191051 | 6.4.7 | 31/10/2026 | 188 | sim |
| RJX3J88 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4429591587468861 | 1.0.0 | nunca | 651 | sim |
| RJX6I60 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7308347130581461 | 1.0.0 | 16/10/2026 | 565 | sim |
| RJX8B77 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC1465786176562933 | 6.4.7 | 03/11/2026 | 61 | sim |
| RJY4B66 | EXPRESSO PREDILETO | Suntech | caminhão | MIC7090259388371418 | 6.5.0 | 03/11/2026 | 656 | sim |
| RJZ4C27 | EXPRESSO PREDILETO | Mix Telematics | caminhão | MIC9841426819471968 | 1.0.0 | 16/10/2026 | 650 | sim |
| RJZ6G46 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC0266017949512051 | 1.0.0 | 16/10/2026 | 523 | sim |
| RKC6G52 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8617190551451723 | 1.0.0 | 15/10/2026 | ? | sim |
| RKC9H51 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9297275654111859 | 1.0.0 | 16/10/2026 | 566 | sim |
| RKG5D43 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9680509118231936 | 1.0.0 | 03/11/2026 | 60 | sim |
| RKG9C05 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5219749327191044 | 1.0.0 | 03/11/2026 | ? | sim |
| RKG9C70 | EXPRESSO PREDILETO | Suntech | caminhão | MIC7175010152851435 | v4.27.7 | 03/11/2026 | 651 | não |
| RKH8A44 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4641788453129285 | 1.0.0 | nunca | 665 | sim |
| RKL5C01 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5534658062311107 | 1.0.0 | nunca | 565 | sim |
| RKO8A59 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7493682282201498 | 6.4.4 | 16/10/2026 | 537 | sim |
| RKQ5D65 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC2050162439234103 | 6.4.7 | 03/11/2026 | 60 | sim |
| RKR8A05 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4341356936278685 | 1.0.0 | 16/10/2026 | 565 | sim |
| RKV3C54 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC1132292478392267 | 6.4.7 | 03/11/2026 | 61 | sim |
| RKV6J92 | EXPRESSO PREDILETO | Mix Telematics | caminhão | MIC6635280015591327 | 1.0.0 | 16/10/2026 | 280 | sim |
| SQV6D04 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5949938607321190 | 6.4.4 | nunca | 189 | sim |
| SQV7F79 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8564316425111713 | 6.3.9 | 16/10/2026 | 565 | sim |
| SRD5I52 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8973648618031794 | 1.0.0 | 16/10/2026 | ? | sim |
| SRE5C94 | EXPRESSO PREDILETO | ? | caminhão | MIC7158763436121431 | 6.5.0 | 03/11/2026 | 531 | sim |
| SRE5D58 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC3817141494817637 | 1.0.0 | nunca | 537 | sim |
| SRG0F03 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4873408674369749 | 1.0.0 | nunca | 265 | sim |
| SRI3E32 | EXPRESSO PREDILETO | Suntech | caminhão | MIC7161855067661432 | 6.4.4 | nunca | 523 | sim |
| SRK8A84 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5267773628771053 | 6.3.8 | nunca | 203 | sim |
| SRN1B14 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7699351591631540 | 1.0.0 | 03/11/2026 | 565 | sim |
| SRP0A45 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9459469802071892 | 6.3.8 | nunca | 203 | sim |
| SRS7F01 | EXPRESSO PREDILETO | ? | caminhão | MIC5378739638051075 | 6.4.7 | 02/11/2026 | 61 | sim |
| SRS7J58 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC1463335332662929 | 1.0.0 | 03/11/2026 | ? | sim |
| SRS7J85 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC3267269851526537 | 6.4.7 | 03/11/2026 | 60 | sim |
| SRU4A50 | EXPRESSO PREDILETO | ? | carro | MIC3337306648346677 | 6.4.5 | 27/10/2025 | 272 | sim |
| SRV2A57 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC3823236370877649 | 6.3.8 | 02/11/2026 | ? | sim |
| SRV2A94 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7295066304401459 | 1.0.0 | 16/10/2026 | 543 | sim |
| SSA7F80 | EXPRESSO PREDILETO | ? | caminhão | MIC8571552569341714 | 1.0.0 | 03/11/2026 | 235 | sim |
| SSC2A28 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC6628888901721325 | 6.3.8 | 16/10/2026 | 188 | sim |
| SSD0C26 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8167315358131633 | 1.0.0 | 16/10/2026 | ? | sim |
| TTM3D82 | EXPRESSO PREDILETO | Suntech | caminhão | MIC0038031378101823 | 6.4.7 | 03/11/2026 | 62 | sim |
| KPR3232 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC4227977648568457 | 6.4.4 | 03/11/2026 | 132 | sim |
| KQS4378 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC0240318275992025 | 6.4.4 | 29/10/2026 | 125 | sim |
| KQT2886 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC2175048789664353 | 6.4.4 | 03/11/2026 | 132 | sim |
| LRA2597 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC9481843474461896 | 6.4.4 | 03/11/2026 | 132 | sim |
| LUO3I89 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC2824659041515651 | 6.4.4 | 06/10/2026 | 147 | sim |
| SRV4F51 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC0245834793632030 | 6.4.0 | 03/11/2026 | 125 | sim |
| TUO7J31 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC0857288188281717 | 6.4.0 | 03/11/2026 | 132 | sim |
| MOV1T23 | FELKA TRANSPORTES E LOGISTICA | Suntech | carro | MIC2531412298395065 | 1.0.0 | 17/10/2025 | 748 | sim |
| RJA7A37 | FELKA TRANSPORTES E LOGISTICA | Suntech | caminhão | MIC5121377371221024 | 1.0.0 | 03/10/2025 | 578 | sim |
| SQV3I75 | FELKA TRANSPORTES E LOGISTICA | Mix Telematics | caminhão | MIC1948651225973899 | v4.11.8 | nunca | 735 | sim |
| SRO0A73 | FELKA TRANSPORTES E LOGISTICA | Mix Telematics | caminhão | MIC7163632440681432 | v4.21.1 | nunca | 761 | sim |
| FGT9B86 | Klabin S.A | Suntech | caminhão | MIC1868677529293739 | 1.0.0 | nunca | 188 | sim |
| RHI3C91 | Klabin S.A | Suntech | caminhão | MIC8011826929391602 | 5.3.7 | nunca | 538 | sim |
| SEQ3J35 | Klabin S.A | Suntech | caminhão | MIC5863698225831172 | 5.3.7 | 31/10/2025 | 538 | sim |
| RJM1B06 | LOGIKA TRANSPORTES | Mix Telematics (novo) | caminhão | MIC8182385509701636 | 6.4.4 | 03/11/2026 | 229 | sim |
| SR07H79 | LOGIKA TRANSPORTES | Mix Telematics | carro | MIC0420088851272205 | 1.0.0 | nunca | 778 | não |
| SRJ7J95 | LOGIKA TRANSPORTES | Mix Telematics | carro | MIC1700087363643403 | 1.0.0 | nunca | 823 | sim |
| SRP8B03 | LOGIKA TRANSPORTES | Mix Telematics (novo) | caminhão | MIC9429535575791886 | 6.4.4 | 03/11/2026 | 228 | sim |
| SRV9I49 | LOGIKA TRANSPORTES | Mix Telematics (novo) | caminhão | MIC5068263214101013 | 1.0.0 | 03/11/2026 | 228 | sim |
| SRW1E70 | LOGIKA TRANSPORTES | Mix Telematics (novo) | caminhão | MIC0079077295181864 | 6.4.4 | 03/11/2026 | 228 | sim |
| C0948 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3098859247566199 | 1.0.0 | nunca | 777 | sim |
| C0958 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC0147064274141932 | 1.0.0 | nunca | 794 | sim |
| C0986 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC4078753995728159 | 1.0.0 | nunca | 859 | sim |
| C1112 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC0135455240141920 | 1.0.0 | nunca | 774 | sim |
| CP004 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC0700118267351403 | 6.4.8 | nunca | 76 | sim |
| CP027 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC7134953037031427 | 1.0.0 | nunca | 748 | sim |
| CR015 | MOSAIC FERTILIZANTES LTDA | ? | caminhão | MIC3151623232186305 | 6.4.8 | nunca | 68 | sim |
| CR018 | MOSAIC FERTILIZANTES LTDA | ? | caminhão | MIC3381027448786765 | 6.5.0 | nunca | 68 | sim |
| CR024 | MOSAIC FERTILIZANTES LTDA | ? | caminhão | MIC3310956338846623 | 6.5.1 | 26/10/2026 | 69 | sim |
| CR027 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC5607914308461121 | 6.4.6 | nunca | 774 | sim |
| CR034 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC6622132453901324 | 6.5.1 | nunca | 69 | sim |
| CR052 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3081748632166165 | 6.4.8 | nunca | 67 | sim |
| CS001 | MOSAIC FERTILIZANTES LTDA | ? | caminhão | MIC0299405858092084 | 6.5.0 | 20/10/2026 | 294 | sim |
| CS002 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC5029412170001006 | 6.5.1 | 20/10/2026 | 68 | sim |
| CS003 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC4350422168198703 | 1.7.0 | 20/10/2026 | ? | sim |
| CS004 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3090046911436183 | 6.4.8 | nunca | 68 | sim |
| CS005 | MOSAIC FERTILIZANTES LTDA | ? | caminhão | MIC3541741939607085 | 6.5.1 | nunca | 75 | sim |
| CS006 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC8391098167751678 | 6.5.0 | nunca | 68 | sim |
| CS007 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC8786854761611757 | 1.0.0 | nunca | 776 | sim |
| CS009 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC6338119162771267 | 6.5.1 | nunca | 68 | sim |
| CS010 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC4170760350828343 | 6.5.1 | nunca | 68 | sim |
| CS011 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC0840450964631683 | 6.5.0 | nunca | 68 | sim |
| MN869 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3064277073476131 | 6.4.8 | nunca | 117 | sim |
| MN870 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC9359292576921872 | 6.5.1 | nunca | 774 | sim |
| MN871 | MOSAIC FERTILIZANTES LTDA | ? | caminhão | MIC7296153883531459 | 6.4.8 | nunca | 67 | sim |
| MOSAIC | MOSAIC FERTILIZANTES LTDA | Mix Telematics | caminhão | MIC9437586587151887 | 1.0.0 | nunca | 777 | sim |
| PC483 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3182182747866367 | 6.5.0 | nunca | 790 | sim |
| TE410 | MOSAIC FERTILIZANTES LTDA | ? | caminhão | MIC3849538047087701 | 6.5.0 | 22/10/2026 | 67 | sim |
| JAO1G85 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC0503435435401009 | 1.0.0 | 11/02/2026 | 538 | sim |
| JAX7B99 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC5193550907101038 | 6.4.4 | 03/11/2026 | 215 | sim |
| JBC1E74 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC4854748663669711 | 6.4.2 | 02/11/2026 | 189 | sim |
| JBL6F29 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC8901831499111780 | 6.4.5 | 17/10/2026 | 147 | sim |
| SQX8C74 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC4803724793129609 | 6.4.5 | 03/11/2026 | 153 | sim |
| SQZ7I20 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC2464350799024931 | 6.4.0 | 02/11/2026 | 138 | sim |
| TTB8B76 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC4489677039908981 | 1.0.0 | 30/10/2026 | 133 | sim |
| TTD7F73 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC4602253209879207 | 6.4.5 | 28/10/2026 | 138 | sim |
| TTW7B29 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC9241813428471848 | 6.4.4 | 30/10/2026 | 662 | sim |
| TUA3D42 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC5714118030701143 | 6.4.4 | 03/11/2026 | 138 | sim |
| TUH4A08 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC2964578494695931 | 6.4.4 | 02/11/2026 | 112 | sim |
| TUI6C37 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC7305583231151461 | 6.4.5 | 03/11/2026 | 214 | sim |
| KZI3171 | SIGHIR ENTERPRISE LTDA | Entrack | caminhão | MIC4871848185139745 | 6.3.14 | 09/10/2026 | 83 | sim |
| MACAE2 | SIGHIR ENTERPRISE LTDA | Entrack | caminhão | MIC4192971182498387 | 1.0.0 | nunca | 530 | sim |
| MALETA_SIGHIR | SIGHIR ENTERPRISE LTDA | Entrack | caminhão | MIC3746566632057495 | 6.5.3 | 29/10/2026 | 209 | não |
| Portaria Predileto | SIGHIR ENTERPRISE LTDA | Suntech | carro | MIC0254242008392039 | 6.5.0 | 01/11/2026 | 192 | sim |
| RKU6C18 | SIGHIR ENTERPRISE LTDA | Mix Telematics (novo) | caminhão | MIC1680328263723363 | v5.1.6 | 15/10/2026 | 794 | sim |
| SIGHIR_POLO | SIGHIR ENTERPRISE LTDA | Suntech | caminhão | MIC2064936644074131 | 6.3.9 | 07/08/2026 | 170 | sim |
| SRA4H41 | SIGHIR ENTERPRISE LTDA | Suntech | carro | MIC7401399559811480 | 6.5.3 | 03/11/2026 | 25 | não |
| SSC2A45 | Scania | Suntech | caminhão | MIC2798322020265599 | 1.0.0 | nunca | 531 | sim |
| FQX0C78 | TRANSMAQUINA S.A. | Suntech | caminhão | MIC4079957157968161 | 1.0.0 | 03/11/2026 | 62 | sim |
| RBC3B63 | TRANSMAQUINA S.A. | Suntech | caminhão | MIC0010150136841795 | 1.0.0 | 30/10/2026 | 272 | sim |
| RBC3H56 | TRANSMAQUINA S.A. | Suntech | caminhão | MIC0175470532591960 | 1.0.0 | 03/11/2026 | 67 | sim |
| RBH3A37 | TRANSMAQUINA S.A. | Suntech | caminhão | MIC0550758668511103 | 1.0.0 | 03/11/2026 | 61 | sim |
| EJX6E23 | TRANSPORTADORA CONTATTO | Suntech | caminhão | MIC8747271166681749 | 6.4.4 | 09/10/2026 | 125 | não |
| KYA9508 | TRANSPORTES MANCHUR | Mix Telematics | caminhão | MIC3982343538817967 | v4.11.6 | nunca | ? | sim |
| SRK8F90 | TRANSPORTES MANCHUR | Mix Telematics (novo) | caminhão | MIC8084049256771617 | 1.0.0 | nunca | 656 | sim |
| BEI5H39 | TRANSPORTES THOMAZ LTDA | Suntech | caminhão | MIC0549488490481101 | 1.0.0 | 03/11/2026 | 543 | sim |
| SRF0J05 | Ziran Logística | Suntech | caminhão | MIC6065320802051213 | 6.5.2 | 03/11/2026 | 20 | sim |
| TUL2A69 | Zirix Enterprise | Suntech | caminhão | MIC2510615791315023 | 1.0.0 | 22/07/2026 | 532 | sim |
