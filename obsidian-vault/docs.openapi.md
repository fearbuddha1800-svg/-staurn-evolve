---
slug: docs.openapi
type: note
graph: gitnexus
---

{
  "openapi": "3.1.0",
  "info": {
    "title": "Signal Relay observational cockpit",
    "version": "1.0.0",
    "description": "Implementation-grounded contract for cockpit_runtime.py. Loopback only; bearer or signed cookie. Not a trading API. Extensible snapshot schemas intentionally do not promise provider-specific fields. Unknown query parameters rejected on documented API routes. /api/neural.health and /api/pine/series are NOT implemented aliases; use /api/neural and /api/pine_series. Authenticated requests to the legacy spellings return 404."
  },
  "servers": [
    {
      "url": "http://127.0.0.1:8490"
    }
  ],
  "security": [
    {
      "BearerAuth": []
    },
    {
      "SessionCookie": []
    }
  ],
  "paths": {
    "/api/strategy_registry": {
      "get": {
        "operationId": "get_strategy_registry",
        "summary": "Read-only strategy registry with bounded cached backtest evidence",
        "description": "No query parameters. Registry refresh disables validation/execution. Returns strategies, execution_available=false and notice; cached revisions can be stale.",
        "responses": {
          "200": {"description": "Registry snapshot", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Snapshot"}}}},
          "400": {"description": "Unexpected query", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
          "401": {"description": "Unauthorized", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
          "403": {"description": "Invalid loopback Host", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}
        }
      }
    },
    "/api/state": {
      "get": {
        "operationId": "get_state",
        "summary": "get state",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/inbox": {
      "get": {
        "operationId": "get_inbox",
                "summary": "get inbox",
                "responses": {
                  "200": {
                    "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
                    "content": {
                      "application/json": {
                        "schema": {
                          "$ref": "#/components/schemas/Rows"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/journal": {
      "get": {
        "operationId": "get_journal",
                "summary": "get journal",
                "responses": {
                  "200": {
                    "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
                    "content": {
                      "application/json": {
                        "schema": {
                          "$ref": "#/components/schemas/Rows"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/mobile": {
      "get": {
        "operationId": "get_mobile",
        "summary": "get mobile",
        "responses": {
          "200": {
            "description": "Authenticated mobile HTML",
            "content": {
              "text/html": {
                "schema": {
                  "type": "string"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/neural": {
      "get": {
        "operationId": "get_neural",
        "summary": "get neural",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Neural"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/latency": {
      "get": {
        "operationId": "get_latency",
        "summary": "get latency",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/lineage": {
      "get": {
        "operationId": "get_lineage",
        "summary": "get lineage",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Rows"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/pine": {
      "get": {
        "operationId": "get_pine",
                "summary": "get pine",
                "responses": {
                  "200": {
                    "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
                    "content": {
                      "application/json": {
                        "schema": {
                          "$ref": "#/components/schemas/Rows"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/strategies": {
      "get": {
        "operationId": "get_strategies",
        "summary": "get strategies",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/health": {
      "get": {
        "operationId": "get_health",
        "summary": "get health",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/channels": {
      "get": {
        "operationId": "get_channels",
                "summary": "get channels",
                "responses": {
                  "200": {
                    "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
                    "content": {
                      "application/json": {
                        "schema": {
                          "$ref": "#/components/schemas/Rows"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/news": {
      "get": {
        "operationId": "get_news",
        "summary": "get news",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/luxalgo": {
      "get": {
        "operationId": "get_luxalgo",
        "summary": "get luxalgo",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/whale": {
      "get": {
        "operationId": "get_whale",
        "summary": "get whale",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/edge": {
      "get": {
        "operationId": "get_edge",
        "summary": "get edge",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/quant": {
      "get": {
        "operationId": "get_quant",
        "summary": "get quant",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/token": {
      "get": {
        "operationId": "get_token",
        "summary": "get token",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Token"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/identity": {
      "get": {
        "operationId": "get_identity",
        "summary": "get identity",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/portfolio": {
      "get": {
        "operationId": "get_portfolio",
        "summary": "get portfolio",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/attribution": {
      "get": {
        "operationId": "get_attribution",
        "summary": "get attribution",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/broker": {
      "get": {
        "operationId": "get_broker",
        "summary": "get broker",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Snapshot"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Resource unavailable",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          }
        }
      }
    },
    "/api/candles": {
      "get": {
        "operationId": "get_candles",
        "summary": "get candles",
        "responses": {
          "200": {
            "description": "Snapshot returned; inspect availability and freshness, not just HTTP status.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Candles"
                }
              }
            }
          },
          "400": {
            "description": "Invalid input or unexpected/duplicate query key",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "401": {
            "description": "Authentication required",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "403": {
            "description": "Loopback Host or same-origin violation",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "404": {
            "description": "Route not found",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "500": {
            "description": "Internal cockpit error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Error"
                }
              }
            }
          },
          "503": {
            "description": "Candle backend unavailable or boundary error",
            "content": {
              "application/json": {
                "schema": {
                  "anyOf": [{"$ref": "#/components/schemas/Error"}, {"$ref": "#/components/schemas/Candles"}]
                }
              }
            }
          }
        },
        "parameters": [
          {
  

... (truncated, 84579 total bytes) ...

