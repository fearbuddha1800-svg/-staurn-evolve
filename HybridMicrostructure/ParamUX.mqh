#ifndef HYBRID_PARAM_UX_MQH
#define HYBRID_PARAM_UX_MQH
//+------------------------------------------------------------------+
//| ParamUX.mqh - User parameters and input validation               |
//+------------------------------------------------------------------+
#property copyright "Copyright©2023. Ritz EAneha©"

//--- Risk & Money Management Parameters
input group "--- Risk & Money Management ---"
input ulong            InpMagicNumber       = 101010;
input group "--- Execution & Target Settings ---"
input double           InpTargetPips        = 200.0;
input double           InpStopLossPips      = 120.0;
input double           InpMaxSpreadPips     = 8.0;
input group "--- Break Even & Trailing Stop ---"
input bool             InpUseTrailing       = true;            // Aktifkan BE & Trailing
input double           InpBreakEvenPips     = 10.0;            // Break Even Trigger (Pips/100 points)
input double           InpTrailingStopPips  = 15.0;            // Trailing Jarak Aman (Pips/150 points)
input double           InpTrailingStepPips  = 5.0;             // Trailing Step (Pips/50 points)
input group "--- Session & Time Filters ---"
input group "--- Microstructure & M1 Filters ---"
input int              InpTickBufferSize    = 500;
input double           InpDevMultiplier     = 1.2;
input ulong            InpVelocityWindowMs  = 800;
input double           InpSnapbackPips      = 2.5;
input bool             InpUseM1Filter       = true;
input int              InpM1ATRPeriod       = 14;
input double           InpMinM1ATRPips      = 1.5;
//+------------------------------------------------------------------+
// Missing configuration contracts restored from the EA's consuming branches.
// Zero/empty defaults are UNCONFIGURED, not recommended trading settings.
// The bridge rejects every entry until a validated backend is implemented.
enum ENUM_HYBRID_MM { MM_FIXED_LOT, MM_RISK_PERCENT };
enum ENUM_HYBRID_RISK_BASE { RISK_BASE_BALANCE, RISK_BASE_EQUITY };
enum ENUM_HYBRID_SLTP { SLTP_FIXED, SLTP_ATR };
enum ENUM_HYBRID_SESSION { SESSION_ALL_DAY, SESSION_WINDOWS };

input group "--- Restored Risk Configuration (configure before validation) ---"
input ENUM_HYBRID_MM InpMMType = MM_FIXED_LOT;
input ENUM_HYBRID_RISK_BASE InpRiskBase = RISK_BASE_EQUITY;
input double InpFixedLot = 0.0;
input double InpRiskPercent = 0.0;
input int InpMaxTotalPositions = 0;
input int InpMaxPositionsPerDirection = 0;
input bool InpUseCooldown = true;
input int InpCooldownSeconds = 0;
input double InpMinDistanceFromLastEntryPips = 0.0;
input int InpMinBarsBetweenEntries = 0;

input group "--- Restored Execution Configuration ---"
input ENUM_HYBRID_SLTP InpSLTPMode = SLTP_FIXED;
input double InpATRMultiplierSL = 0.0;
input double InpATRMultiplierTP = 0.0;
input bool InpUseVWAPTarget = false;
input ulong InpDeviationPoints = 0;
input bool InpRequireExtraMove = true;
input double InpExtraMovePips = 0.0;

input group "--- Restored Session Configuration (broker time) ---"
input ENUM_HYBRID_SESSION InpSessionMode = SESSION_WINDOWS;
input bool InpAvoidRollover = true;
input string InpSession1_Start = "";
input string InpSession1_End = "";
input string InpSession2_Start = "";
input string InpSession2_End = "";

input group "--- Restored Trend Configuration ---"
input bool InpUseTrendFilter = true;
input bool InpUseH1Trend = true;
input bool InpUseM15Trend = true;
input bool InpUseM5Trend = true;
input int InpH1MAPeriod = 0;
input int InpM15MAPeriod = 0;
input int InpM5MAPeriod = 0;
input ENUM_MA_METHOD InpMAMethod = MODE_SMA;
input bool InpUseM5Setup = true;
input bool InpRequireM5CandleBias = true;

input group "--- Restored M1 Structure Configuration ---"
input double InpMaxM1ATRPips = 0.0; // Existing consumer: zero disables upper cap.
input bool InpUseM1Structure = true;
input double InpMinWickRatio = 0.0;
input double InpMinBodyRatio = 0.0;
input bool InpRequireCandleBias = true;
input bool InpRequireCloseLocation = true;
input double InpMinCloseLocation = 0.0;
#endif
