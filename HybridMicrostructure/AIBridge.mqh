#ifndef HYBRID_AI_BRIDGE_MQH
#define HYBRID_AI_BRIDGE_MQH
//+------------------------------------------------------------------+
//| AIBridge.mqh - AI Bridge & Decision Intelligence               |
//+------------------------------------------------------------------+
#property copyright "Copyright©2023. Ritz EAneha©"

//--- AI Bridge States
input group "--- AI Bridge Configuration ---"
input bool             InpAIBridgeEnabled  = true;           // AI Bridge aktif
input ENUM_TIMEFRAMES  InpAIBridgeTimeframe = PERIOD_M15;    // AI Bridge timeframe
input double           InpAIRiskTolerance   = 0.5;           // AI Risk tolerance 0-1
input group "--- AI Bridge Signal Filtering ---"
input bool             InpAIFilterSnapback  = true;          // Filter signals via snapback
input bool             InpAIMTFConfirm      = true;          // Require MTF confirmation
input bool             InpAIUseVelocity     = true;          // Use velocity detection
//+------------------------------------------------------------------+
// Compatibility snapshot consumed by OnTick; refreshed during initialization.
struct SCoreBridgeParams
{
    bool InpAIFilterSnapback;
    bool InpAIMTFConfirm;
};
SCoreBridgeParams g_coreParams;

// No validated inference backend is connected. Returning false is intentional.
// The current EA ignores this result; AIBridge_Confirm remains the final gate.
bool AIBridge_Init()
{
    g_coreParams.InpAIFilterSnapback = InpAIFilterSnapback;
    g_coreParams.InpAIMTFConfirm = InpAIMTFConfirm;
    Print("[AI BRIDGE] Unavailable: no validated backend; all entries rejected.");
    return false;
}

// Signature matches both BUY and SELL call sites. Disabled AI is not a bypass.
bool AIBridge_Confirm(
    const ENUM_ORDER_TYPE order_type,
    const double entry_price,
    const MqlTick &tick,
    const bool is_high_velocity,
    const double vwap,
    const double upper_band,
    const double lower_band,
    const double std_dev,
    const double extreme_peak,
    const int atr_m1_handle,
    const int ma_h1_handle,
    const int ma_m15_handle,
    const int ma_m5_handle)
{
    return false;
}
#endif
