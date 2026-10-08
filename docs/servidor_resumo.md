# Servidor de produção — resumo da frota (gerado)

> Gerado por `tools/servidor.py resumo` em 08/10/2026 10:46 (BRT), só leitura da API (`https://sighir.com:8000/api/v2`). Não edite: "sincronizar os documentos" refaz. Números mudam todo dia — para uma placa específica use o Helper (`helper.py veiculo PLACA`).

**146 instalações** em 19 empresas · 141 operando · anomalias abertas: 244 · firmware mais novo no catálogo: **v6.4.7** (2026-09-01)

## Por telemetria

| telemetria | instalações |
|---|---|
| Mix Telematics (novo) | 82 |
| Suntech | 42 |
| Mix Telematics | 11 |
| ? | 7 |
| Entrack | 4 |

## Última comunicação (último log recebido)

Na MiX de empresa que não repassa logs, "sem comunicação" pode ser normal (`telemetrias.md`).

| há quanto tempo | instalações |
|---|---|
| < 1 dia | 65 |
| 1–7 dias | 4 |
| 7–30 dias | 3 |
| > 30 dias | 14 |
| nunca | 60 |

## Calibração do sensor (data da calibração corrente, regra de 1 ano)

| situação | instalações |
|---|---|
| vencida (> 365 dias) | 61 |
| vence em ≤ 30 dias | 0 |
| em dia | 72 |
| sem dado | 13 |

## Firmware reportado × catálogo

`software_version` só muda no check-update via Wi-Fi; `1.0.0` = nunca reportou (`portal_app.md` §4).

| versão reportada | instalações |
|---|---|
| 1.0.0 | 66 |
| 6.4.4 | 19 |
| 6.4.7 | 12 |
| 6.4.8 | 8 |
| 6.3.8 | 6 |
| 6.4.0 | 5 |
| 6.4.5 | 5 |
| 6.3.9 | 4 |
| 6.4.6 | 3 |
| 6.5.0 | 3 |
| 6.3.11 | 3 |
| 5.3.7 | 2 |
| 6.3.12 | 2 |
| v4.11.6 | 1 |
| v5.1.6 | 1 |
| v4.11.8 | 1 |
| v4.21.1 | 1 |
| v4.27.7 | 1 |
| 6.4.3 | 1 |
| 6.4.2 | 1 |
| 6.3.14 | 1 |

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
| calibracao | 81 |
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
| EXPRESSO PREDILETO | 62 | ?, Mix Telematics, Mix Telematics (novo), Suntech | 21 | 23 |
| MOSAIC FERTILIZANTES LTDA | 29 | ?, Mix Telematics, Mix Telematics (novo) | 29 | 19 |
| RICKER TRANSPORTES LTDA | 12 | Suntech | 1 | 2 |
| SIGHIR ENTERPRISE LTDA | 7 | Entrack, Mix Telematics (novo), Suntech | 4 | 3 |
| FAJE LOGISTICA E TRANSPORTE | 7 | Suntech | 0 | 0 |
| LOGIKA TRANSPORTES | 6 | Mix Telematics, Mix Telematics (novo) | 3 | 2 |
| FELKA TRANSPORTES E LOGISTICA | 4 | Mix Telematics, Suntech | 4 | 4 |
| Klabin S.A | 3 | Suntech | 3 | 2 |
| TRANSMAQUINA S.A. | 3 | ?, Suntech | 1 | 0 |
| TRANSPORTES MANCHUR | 2 | Mix Telematics, Mix Telematics (novo) | 2 | 1 |
| BELLA VIA TRANSPORTES LTDA | 2 | Suntech | 2 | 2 |
| ATVOS BIOENERGIA DO PONTAL S.A | 2 | Mix Telematics (novo) | 2 | 0 |
| TRANSPORTES THOMAZ LTDA | 1 | Suntech | 0 | 1 |
| Scania | 1 | Suntech | 1 | 1 |
| Zirix Enterprise | 1 | Suntech | 1 | 1 |
| CONSTRUTORA CENTRO LESTE S/A | 1 | Entrack | 0 | 0 |
| Andrade Telemetria Rastreament | 1 | ? | 1 | 0 |
| DETECTOR LTDA | 1 | Suntech | 1 | 0 |
| TRANSPORTADORA CONTATTO | 1 | Suntech | 1 | 0 |

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
| UBR9J42 | ATVOS BIOENERGIA DO PONTAL S.A | Mix Telematics (novo) | caminhão | MIC8391422140241678 | 6.4.0 | nunca | 106 | sim |
| UBU2I57 | ATVOS BIOENERGIA DO PONTAL S.A | Mix Telematics (novo) | caminhão | MIC3460577981536923 | 6.4.0 | nunca | 106 | sim |
| TESTE ENTRACK | Andrade Telemetria Rastreament | ? | caminhão | MIC8708795299331741 | 6.3.11 | nunca | 166 | sim |
| EOJ5I60 | BELLA VIA TRANSPORTES LTDA | Suntech | caminhão | MIC0990885423811983 | 1.0.0 | nunca | 527 | sim |
| SPX4A02 | BELLA VIA TRANSPORTES LTDA | Suntech | caminhão | MIC5738341846131147 | 1.0.0 | nunca | 512 | sim |
| TFE6H05 | CONSTRUTORA CENTRO LESTE S/A | Entrack | caminhão | MIC8767790427121753 | 6.4.4 | 08/10/2026 | 133 | sim |
| SYM4F89 | DETECTOR LTDA | Suntech | caminhão | MIC0014246467341799 | 1.0.0 | 20/07/2026 | 177 | sim |
| EMP009 | EXPRESSO PREDILETO | ? | caminhão | MIC0483049134592268 | 1.0.0 | 03/11/2025 | 512 | sim |
| EMPRIO | EXPRESSO PREDILETO | Suntech | caminhão | MIC7491597966861498 | 6.3.11 | 03/08/2026 | 147 | sim |
| LUA5E58 | EXPRESSO PREDILETO | Mix Telematics | caminhão | MIC1009016058992021 | 1.0.0 | 06/07/2026 | 42 | sim |
| LUE9A29 | EXPRESSO PREDILETO | Mix Telematics | caminhão | MIC9935714618981987 | 6.3.12 | 07/10/2026 | 258 | não |
| PPQ9017 | EXPRESSO PREDILETO | Mix Telematics | carro | MIC5282201573701056 | 6.5.0 | 07/10/2026 | 97 | sim |
| QRH8I97 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4875498327299753 | 1.0.0 | 07/10/2026 | 506 | sim |
| QRM7G63 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC2654251818395311 | 1.0.0 | 07/10/2026 | ? | sim |
| QRM8G13 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7055839215641411 | 6.3.9 | 08/10/2026 | 245 | sim |
| QRM8G28 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7182391889581436 | 6.3.12 | 07/10/2026 | 209 | não |
| QRM8G34 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8826555221551765 | 1.0.0 | nunca | 512 | sim |
| RJE2J65 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC2948811743345899 | 6.3.11 | 08/10/2026 | 246 | sim |
| RJE6F03 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC0374648453142159 | 6.3.8 | 22/07/2026 | 254 | não |
| RJG6H37 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC6795935748551359 | 6.3.8 | 08/10/2026 | 162 | sim |
| RJI1C01 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC0155178983031940 | 1.0.0 | 08/10/2026 | 190 | sim |
| RJK1D03 | EXPRESSO PREDILETO | Suntech | caminhão | MIC3474296550936951 | 6.4.4 | 08/10/2026 | 246 | sim |
| RJM4H64 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8443966547941688 | 1.0.0 | nunca | 527 | sim |
| RJN8B5 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9563057659771912 | 6.4.7 | nunca | 511 | sim |
| RJO6I53 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7952031891471590 | 1.0.0 | nunca | ? | sim |
| RJP4I71 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7701672413901540 | 1.0.0 | 08/10/2026 | 510 | sim |
| RJQ3F02 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC1563513907743129 | 6.4.7 | 08/10/2026 | 162 | sim |
| RJR7C09 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9272967618681854 | 1.0.0 | 08/10/2026 | ? | sim |
| RJS5A13 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9558193970261911 | 1.0.0 | 08/10/2026 | 539 | sim |
| RJT5E02 | EXPRESSO PREDILETO | Suntech | caminhão | MIC3004645420106011 | 6.4.8 | 08/10/2026 | 112 | sim |
| RJT8B80 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5283053322081056 | 1.0.0 | 08/10/2026 | ? | sim |
| RJT9G28 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4169182339378341 | 1.0.0 | 08/10/2026 | ? | sim |
| RJV1A55 | EXPRESSO PREDILETO | ? | caminhão | MIC5256069479191051 | 6.4.7 | 08/10/2026 | 162 | sim |
| RJX3J88 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4429591587468861 | 1.0.0 | nunca | 625 | sim |
| RJX6I60 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7308347130581461 | 1.0.0 | 08/10/2026 | 539 | sim |
| RJX8B77 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC1465786176562933 | 6.4.7 | 08/10/2026 | 35 | sim |
| RJY4B66 | EXPRESSO PREDILETO | Suntech | caminhão | MIC7090259388371418 | 6.3.9 | 08/10/2026 | 630 | sim |
| RJZ4C27 | EXPRESSO PREDILETO | Mix Telematics | caminhão | MIC9841426819471968 | 1.0.0 | 08/10/2026 | 624 | sim |
| RJZ6G46 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC0266017949512051 | 1.0.0 | 08/10/2026 | 497 | sim |
| RKC6G52 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8617190551451723 | 1.0.0 | 08/10/2026 | ? | sim |
| RKC9H51 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9297275654111859 | 1.0.0 | 08/10/2026 | 540 | sim |
| RKG5D43 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9680509118231936 | 1.0.0 | 08/10/2026 | 34 | sim |
| RKG9C05 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5219749327191044 | 1.0.0 | 08/10/2026 | ? | sim |
| RKG9C70 | EXPRESSO PREDILETO | Suntech | caminhão | MIC7175010152851435 | v4.27.7 | 08/10/2026 | 625 | sim |
| RKH8A44 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4641788453129285 | 1.0.0 | nunca | 639 | sim |
| RKL5C01 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5534658062311107 | 1.0.0 | nunca | 539 | sim |
| RKO8A59 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7493682282201498 | 6.4.4 | 08/10/2026 | 511 | sim |
| RKQ5D65 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC2050162439234103 | 6.4.7 | 08/10/2026 | 34 | sim |
| RKR8A05 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4341356936278685 | 1.0.0 | 08/10/2026 | 539 | sim |
| RKV3C54 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC1132292478392267 | 6.4.7 | 08/10/2026 | 35 | sim |
| RKV6J92 | EXPRESSO PREDILETO | Mix Telematics | caminhão | MIC6635280015591327 | 1.0.0 | 08/10/2026 | 254 | sim |
| SQV6D04 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5949938607321190 | 6.4.4 | nunca | 163 | sim |
| SQV7F79 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8564316425111713 | 6.3.9 | 08/10/2026 | 539 | sim |
| SRD5I52 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8973648618031794 | 1.0.0 | 08/10/2026 | ? | sim |
| SRE5D58 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC3817141494817637 | 1.0.0 | nunca | 511 | sim |
| SRG0F03 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC4873408674369749 | 1.0.0 | nunca | 239 | sim |
| SRI3E32 | EXPRESSO PREDILETO | Suntech | caminhão | MIC7161855067661432 | 6.4.4 | nunca | 497 | sim |
| SRK8A84 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC5267773628771053 | 6.3.8 | nunca | 177 | sim |
| SRN1B14 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7699351591631540 | 1.0.0 | 08/10/2026 | 539 | sim |
| SRP0A45 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC9459469802071892 | 6.3.8 | nunca | 177 | sim |
| SRS7J58 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC1463335332662929 | 1.0.0 | 20/09/2026 | ? | sim |
| SRS7J85 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC3267269851526537 | 6.4.7 | 08/10/2026 | 34 | sim |
| SRU4A50 | EXPRESSO PREDILETO | ? | carro | MIC3337306648346677 | 6.4.5 | 27/10/2025 | 246 | sim |
| SRV2A57 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC3823236370877649 | 6.3.8 | nunca | ? | sim |
| SRV2A94 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC7295066304401459 | 1.0.0 | 08/10/2026 | 517 | sim |
| SSA7F80 | EXPRESSO PREDILETO | ? | caminhão | MIC8571552569341714 | 1.0.0 | 07/10/2026 | 209 | sim |
| SSC2A28 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC6628888901721325 | 6.3.8 | 18/08/2026 | 162 | sim |
| SSD0C26 | EXPRESSO PREDILETO | Mix Telematics (novo) | caminhão | MIC8167315358131633 | 1.0.0 | 08/10/2026 | ? | sim |
| TTM3D82 | EXPRESSO PREDILETO | Suntech | caminhão | MIC0038031378101823 | 6.4.7 | 08/10/2026 | 79 | sim |
| KPR3232 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC4227977648568457 | 6.4.4 | 08/10/2026 | 106 | sim |
| KQS4378 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC0240318275992025 | 6.4.4 | 08/10/2026 | 99 | sim |
| KQT2886 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC2175048789664353 | 6.4.4 | 08/10/2026 | 106 | sim |
| LRA2597 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC9481843474461896 | 6.4.4 | 08/10/2026 | 106 | sim |
| LUO3I89 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC2824659041515651 | 6.4.4 | 06/10/2026 | 121 | sim |
| SRV4F51 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC0245834793632030 | 6.4.0 | 08/10/2026 | 99 | sim |
| TUO7J31 | FAJE LOGISTICA E TRANSPORTE | Suntech | caminhão | MIC0857288188281717 | 6.4.0 | 08/10/2026 | 106 | sim |
| MOV1T23 | FELKA TRANSPORTES E LOGISTICA | Suntech | carro | MIC2531412298395065 | 1.0.0 | 17/10/2025 | 722 | sim |
| RJA7A37 | FELKA TRANSPORTES E LOGISTICA | Suntech | caminhão | MIC5121377371221024 | 1.0.0 | 03/10/2025 | 552 | sim |
| SQV3I75 | FELKA TRANSPORTES E LOGISTICA | Mix Telematics | caminhão | MIC1948651225973899 | v4.11.8 | nunca | 709 | sim |
| SRO0A73 | FELKA TRANSPORTES E LOGISTICA | Mix Telematics | caminhão | MIC7163632440681432 | v4.21.1 | nunca | 735 | sim |
| FGT9B86 | Klabin S.A | Suntech | caminhão | MIC1868677529293739 | 1.0.0 | nunca | 162 | sim |
| RHI3C91 | Klabin S.A | Suntech | caminhão | MIC8011826929391602 | 5.3.7 | nunca | 512 | sim |
| SEQ3J35 | Klabin S.A | Suntech | caminhão | MIC5863698225831172 | 5.3.7 | 31/10/2025 | 512 | sim |
| RJM1B06 | LOGIKA TRANSPORTES | Mix Telematics (novo) | caminhão | MIC8182385509701636 | 6.4.4 | 08/10/2026 | 203 | sim |
| SR07H79 | LOGIKA TRANSPORTES | Mix Telematics | carro | MIC0420088851272205 | 1.0.0 | nunca | 752 | sim |
| SRJ7J95 | LOGIKA TRANSPORTES | Mix Telematics | carro | MIC1700087363643403 | 1.0.0 | nunca | 797 | sim |
| SRP8B03 | LOGIKA TRANSPORTES | Mix Telematics (novo) | caminhão | MIC9429535575791886 | 1.0.0 | nunca | 202 | sim |
| SRV9I49 | LOGIKA TRANSPORTES | Mix Telematics (novo) | caminhão | MIC5068263214101013 | 1.0.0 | 08/10/2026 | 202 | sim |
| SRW1E70 | LOGIKA TRANSPORTES | Mix Telematics (novo) | caminhão | MIC0079077295181864 | 6.4.4 | 08/10/2026 | 202 | sim |
| C 948 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC4727975779229457 | 1.0.0 | nunca | 748 | sim |
| C 958 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC0147064274141932 | 1.0.0 | nunca | 768 | sim |
| C1112 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC0135455240141920 | 1.0.0 | nunca | 748 | sim |
| C948 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3098859247566199 | 1.0.0 | nunca | 751 | sim |
| C986 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC4078753995728159 | 1.0.0 | nunca | 833 | sim |
| CP001 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC6622132453901324 | 6.4.8 | nunca | 69 | sim |
| CP004 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC0700118267351403 | 6.4.8 | nunca | 50 | sim |
| CP027 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC7134953037031427 | 1.0.0 | nunca | 722 | sim |
| CR 34 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC7284041558651457 | 6.4.8 | nunca | 43 | sim |
| CR009 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC6338119162771267 | 6.5.0 | nunca | 42 | sim |
| CR018 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC0485257155082270 | 1.0.0 | nunca | 751 | sim |
| CR27 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC5607914308461121 | 6.4.6 | nunca | 748 | sim |
| CR52 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3081748632166165 | 6.4.8 | nunca | 41 | sim |
| CS001 | MOSAIC FERTILIZANTES LTDA | ? | caminhão | MIC0299405858092084 | 6.4.7 | nunca | 750 | sim |
| CS002 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC5029412170001006 | 6.4.7 | nunca | 769 | sim |
| CS003 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC4350422168198703 | 6.4.7 | nunca | 42 | sim |
| CS004 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC7403205350531480 | 1.0.0 | nunca | 762 | sim |
| CS005 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC4170760350828343 | 6.4.8 | nunca | 42 | sim |
| CS006 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC6377937822871275 | 1.0.0 | nunca | 763 | sim |
| CS007 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC8786854761611757 | 1.0.0 | nunca | 750 | sim |
| CS008 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC0840450964631683 | 6.4.4 | nunca | 42 | sim |
| CS010 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC5040407178981008 | 1.0.0 | nunca | 750 | sim |
| CS011 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3090046911436183 | 6.4.8 | nunca | 42 | sim |
| MN869 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3064277073476131 | 6.4.8 | nunca | 91 | sim |
| MN870 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC7807516597511561 | 1.0.0 | nunca | 748 | sim |
| MOSAIC | MOSAIC FERTILIZANTES LTDA | Mix Telematics | caminhão | MIC9437586587151887 | 1.0.0 | nunca | 751 | sim |
| PC483 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC3182182747866367 | 6.4.6 | nunca | 764 | sim |
| RE 624 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC8391098167751678 | 6.4.7 | nunca | 752 | sim |
| RE624 | MOSAIC FERTILIZANTES LTDA | Mix Telematics (novo) | caminhão | MIC9359292576921872 | 6.4.4 | nunca | 748 | sim |
| JAO1G85 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC0503435435401009 | 1.0.0 | 11/02/2026 | 512 | sim |
| JAX7B99 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC5193550907101038 | 6.4.4 | 08/10/2026 | 189 | sim |
| JBC1E74 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC4854748663669711 | 6.4.2 | 08/10/2026 | 163 | sim |
| JBL6F29 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC8901831499111780 | 6.4.5 | 07/10/2026 | 121 | sim |
| SQX8C74 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC4803724793129609 | 6.4.5 | 08/10/2026 | 127 | sim |
| SQZ7I20 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC2464350799024931 | 6.4.0 | 07/10/2026 | 112 | sim |
| TTB8B76 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC4489677039908981 | 1.0.0 | 07/10/2026 | 107 | sim |
| TTD7F73 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC4602253209879207 | 6.4.5 | 07/10/2026 | 112 | sim |
| TTW7B29 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC9241813428471848 | 6.4.4 | 02/10/2026 | 636 | sim |
| TUA3D42 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC5714118030701143 | 6.4.4 | 08/10/2026 | 112 | sim |
| TUH4A08 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC2964578494695931 | 6.4.4 | 08/10/2026 | 86 | sim |
| TUI6C37 | RICKER TRANSPORTES LTDA | Suntech | caminhão | MIC7305583231151461 | 6.4.5 | 07/10/2026 | 188 | sim |
| KZI3171 | SIGHIR ENTERPRISE LTDA | Entrack | caminhão | MIC4871848185139745 | 6.3.14 | 05/10/2026 | 57 | sim |
| MACAE | SIGHIR ENTERPRISE LTDA | Entrack | caminhão | MIC4192971182498387 | 1.0.0 | nunca | 504 | sim |
| MALETA_SIGHIR | SIGHIR ENTERPRISE LTDA | Entrack | caminhão | MIC3746566632057495 | 6.4.6 | 24/09/2026 | 183 | não |
| Portaria Predileto | SIGHIR ENTERPRISE LTDA | Suntech | carro | MIC0254242008392039 | 6.5.0 | 06/10/2026 | 166 | sim |
| RKU6C18 | SIGHIR ENTERPRISE LTDA | Mix Telematics (novo) | caminhão | MIC1680328263723363 | v5.1.6 | 08/10/2026 | 768 | sim |
| SIGHIR_POLO | SIGHIR ENTERPRISE LTDA | Suntech | caminhão | MIC2064936644074131 | 6.3.9 | 07/08/2026 | 144 | sim |
| SRA4H41 | SIGHIR ENTERPRISE LTDA | Mix Telematics (novo) | carro | MIC4791703356689585 | 6.4.3 | 22/07/2026 | 517 | não |
| SSC2A45 | Scania | Suntech | caminhão | MIC2798322020265599 | 1.0.0 | nunca | 505 | sim |
| FQX0C78 | TRANSMAQUINA S.A. | Suntech | caminhão | MIC4079957157968161 | 1.0.0 | 08/10/2026 | 36 | sim |
| RBC3B63 | TRANSMAQUINA S.A. | Suntech | caminhão | MIC0010150136841795 | 1.0.0 | 08/10/2026 | 246 | sim |
| RBH3A37 | TRANSMAQUINA S.A. | ? | caminhão | MIC0550758668511103 | 1.0.0 | nunca | ? | sim |
| EJX6E23 | TRANSPORTADORA CONTATTO | Suntech | caminhão | MIC8747271166681749 | 6.4.4 | 29/09/2026 | 99 | sim |
| KYA9508 | TRANSPORTES MANCHUR | Mix Telematics | caminhão | MIC3982343538817967 | v4.11.6 | nunca | ? | sim |
| SRK8F90 | TRANSPORTES MANCHUR | Mix Telematics (novo) | caminhão | MIC8084049256771617 | 1.0.0 | nunca | 630 | sim |
| BEI5H39 | TRANSPORTES THOMAZ LTDA | Suntech | caminhão | MIC0549488490481101 | 1.0.0 | 08/10/2026 | 517 | sim |
| TUL2A69 | Zirix Enterprise | Suntech | caminhão | MIC2510615791315023 | 1.0.0 | 22/07/2026 | 506 | sim |
