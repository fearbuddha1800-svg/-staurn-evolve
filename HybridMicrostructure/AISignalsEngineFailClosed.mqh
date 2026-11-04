// Fail-closed replacement for AISignalsEngine.mqh, included by the main EA.
// Do not include both engines: they intentionally expose the same interface.
// No inference backend has been implemented or validated.
#ifndef HYBRID_AI_SIGNALS_ENGINE_FAIL_CLOSED_MQH
#define HYBRID_AI_SIGNALS_ENGINE_FAIL_CLOSED_MQH

struct SSignal
{
   int Type;                    // 2 = HOLD; this module never emits BUY/SELL.
   double Confidence;
   double EntryPrice;
   double StopLoss;
   double TakeProfit;
   int Timeframe;
   string Source;
   string Reason;
   datetime Timestamp;
   int MagicNumber;
   double ExpectedValue;
   double WinProbability;
};

class CAISignalsEngine
{
public:
   bool Initialize()
   {
      Print("[AI BLOCKED] No validated inference backend. Initialization refused.");
      return false;
   }

   SSignal GenerateSignal(const string &symbol,
                          int primaryTimeframe = PERIOD_M15)
   {
      SSignal signal;
      signal.Type = 2;
      signal.Confidence = 0.0;
      signal.EntryPrice = 0.0;
      signal.StopLoss = 0.0;
      signal.TakeProfit = 0.0;
      signal.Timeframe = primaryTimeframe;
      signal.Source = "UNAVAILABLE";
      signal.Reason = "No validated inference backend for " + symbol;
      signal.Timestamp = TimeCurrent();
      signal.MagicNumber = 0;
      signal.ExpectedValue = 0.0;
      signal.WinProbability = 0.0;
      return signal;
   }
};

CAISignalsEngine g_aiEngine;

#endif
