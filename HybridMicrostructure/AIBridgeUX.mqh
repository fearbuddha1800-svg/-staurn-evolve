#ifndef HYBRID_AI_BRIDGE_UX_MQH
#define HYBRID_AI_BRIDGE_UX_MQH
//+------------------------------------------------------------------+
//| AIBridgeUX.mqh - AI Bridge User Interface & Panel            |
//+------------------------------------------------------------------+
#property copyright "Copyright©2023. Ritz EAneha"

//--- AI Panel Configuration
input group "--- AI Panel Settings ---"
input bool             InpAIPanelShow       = true;          // Show AI panel
input color            InpAIPanelBackground = clrDarkGray;   // Panel background
input color            InpAIPanelText        = clrWhite;      // Text color
input group "--- Panel Data Sources ---"
input ENUM_TIMEFRAMES  InpPanelH1Timeframe  = PERIOD_H1;      // H1 timeframe for panel
input ENUM_TIMEFRAMES  InpPanelM15Timeframe = PERIOD_M15;    // M15 timeframe for panel
input ENUM_TIMEFRAMES  InpPanelM5Timeframe  = PERIOD_M5;      // M5 timeframe for panel
input group "--- Panel Display Options ---"
input bool               InpPanelShowVWAP     = true;          // Show VWAP line
input bool               InpPanelShowBands    = true;          // Show deviation bands
input bool               InpPanelShowAIState  = true;          // Show AI state
input bool               InpPanelShowTrend    = true;          // Show trend alignment
//+------------------------------------------------------------------+
// Compatibility lifecycle hooks only: no panel objects or outcome tracker exist.
// Do not imply inference, outcome tracking, or auto-tuning has occurred.
void AIBridge_TickMaintenance()
{
}

void AIBridge_Deinit()
{
}
#endif
