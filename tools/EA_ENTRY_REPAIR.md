# EA entry repair — 2026-11-04

Scope: only Hybrid_Microstructure_EA_V1.0.mq5 and this new note. Headers untouched.
No dependencies, children, loops, commit, trading, or external messages.

## Impact and concrete references

Read AGENTS.md, docs/MT5_ENGINEERING_STATUS.md, tools/EA_REPAIR_NOTES.md,
and .claude/skills/gitnexus-impact-analysis/SKILL.md before edits.
`rtk proxy gitnexus list` bound the sole index to staurn-evolve at
/code/Personal, indexed commit fb9b66e; checkout HEAD e053f54. The registry
name differs from AGENTS.md's signal-relay. All impact commands explicitly
bound --repo /code/Personal. Index freshness was not established.

Ran `rtk proxy gitnexus impact NAME --direction upstream --repo /code/Personal`
for each changed existing function: OnInit, OnTick, ProcessSweepLogic,
CheckMTFConfirmation. Every command exited 1: Target not found; risk UNKNOWN;
impactedCount null. No graph callers or execution processes were resolved.
Graph/transitive risk remains unresolved, not LOW or evidence of unused code.
The user's explicit UNKNOWN fallback authorizes these surgical repairs with
concrete text confirmation; no graph-clean claim is made.

`rg` across *.mq* confirmed main OnInit and OnTick are terminal event handlers;
legacy AISignalsEngine also defines event handlers but is now excluded from
this EA. Main OnTick is the sole concrete ProcessSweepLogic caller (seven
arguments) and sole CheckMTFConfirmation caller (now signal type argument).
Original AISignalsEngine.mqh lines 1006–1026 and 1037 establish 0 BUY, 1 SELL,
2 HOLD. Existing GetTFTrend uses CopyBuffer and CopyRates at shift 1 and
rejects invalid handles/missing data. Its body was not changed.

## Behavior and limitations

Restored H1 Print semicolon; accepted const SSignal reference as seventh sweep
argument; required matching direction in each final sweep branch. Snapback and
MTF rejection reset state and return before sweep processing. No confidence or
prediction is manufactured. MTF checks all H1/M15/M5 against signal direction
through existing configured handles, with no new period/default choices. If
trend flags did not create all three handles, enabled AI MTF confirmation
rejects; no handles are silently substituted or filters bypassed.

The fail-closed replacement include removes the legacy engine from this entry
include tree. AIBridge_Init false returns INIT_FAILED; its current stub always
refuses. The replacement engine also refuses Initialize and emits only HOLD.
No neural implementation or header edits. Existing initialization banner order
and unrelated risk sizing/position management remain outside this repair.

## Check evidence

- Source assertions PASS: 33 function declarations all at global brace depth;
  balanced braces, no negative nesting (before and after); exact include/init,
  seventh argument, both rejection blocks, 1 SELL/0 BUY, three GetTFTrend calls,
  no iMA inside CheckMTFConfirmation, no confidence assignment, no added trailing
  whitespace. This is lexical/source evidence only, not an MQL parser/typecheck.
- `rtk proxy python tools/ea_readiness.py` exits 1 overall. Main EA reports five
  source files, findings [], needs_metaeditor_compile, compiled false.
  ResearchFramework remains blocked on unsupported delegate_task and invalid
  decorative preprocessor; untouched.
- Main EA was already untracked; git diff cannot show its incremental changes.
  Exact unified diff below compares the pre-edit /tmp snapshot. No commit made.
- No MQL linter/typechecker or accessible MetaEditor. No compile/backtest/demo
  readiness claim. The program may retain blockers outside these source checks.

## Exact incremental diff

```diff
--- before/Hybrid_Microstructure_EA_V1.0.mq5
+++ after/Hybrid_Microstructure_EA_V1.0.mq5
@@ -22,7 +22,7 @@
 #include <HybridMicrostructure\ParamUX.mqh>
 #include <HybridMicrostructure\AIBridge.mqh>
 #include <HybridMicrostructure\AIBridgeUX.mqh>
-#include <HybridMicrostructure\AISignalsEngine.mqh>
+#include <HybridMicrostructure\AISignalsEngineFailClosed.mqh>

 //+------------------------------------------------------------------+
 //| DATA STRUCTURE                                                    |
@@ -110,7 +110,7 @@

         if (handle_ma_h1 == INVALID_HANDLE)
         {
-            Print("[INIT ERROR] Failed to create H1 MA handle")
+            Print("[INIT ERROR] Failed to create H1 MA handle");
             return (INIT_FAILED);
         }
     }
@@ -161,7 +161,11 @@
     last_entry_bar_m5 = 0;

     Print("--------------------------------------------------");
-    AIBridge_Init();
+    if (!AIBridge_Init())
+    {
+        Print("[INIT ERROR] AI Bridge initialization refused");
+        return (INIT_FAILED);
+    }

     Print(" Hybrid Microstructure EA V1.0 INITIALIZED");
     Print(" Symbol: ", _Symbol);
@@ -265,22 +269,20 @@
         aiSignal = g_aiEngine.GenerateSignal(_Symbol, InpAIBridgeTimeframe);

         // Process AI signal through core engine
-        if(aiSignal.Type != 2 && aiSignal.Confidence > InpAIRiskTolerance)
+        if((aiSignal.Type == 0 || aiSignal.Type == 1) && aiSignal.Confidence > InpAIRiskTolerance)
         {
             // Check snapback filter if enabled
             if(g_coreParams.InpAIFilterSnapback && !CheckSnapbackCondition(vwap, upper_band, lower_band))
             {
-                // Snapback filter active - may override or modify signal
-                if(aiSignal.Type == 0) aiSignal.EntryPrice = MathMax(aiSignal.EntryPrice, vwap + InpSnapbackPips * _Point);
-                else if(aiSignal.Type == 1) aiSignal.EntryPrice = MathMin(aiSignal.EntryPrice, vwap - InpSnapbackPips * _Point);
+                ResetSweepState();
+                return;
             }

             // Check MTF confirmation if enabled
-            if(g_coreParams.InpAIMTFConfirm && !CheckMTFConfirmation())
+            if(g_coreParams.InpAIMTFConfirm && !CheckMTFConfirmation(aiSignal.Type))
             {
-                // MTF filter - reduce position size or modify SL/TP
-                aiSignal.StopLoss = NormalizeDouble(aiSignal.StopLoss, _Digits);
-                aiSignal.TakeProfit = NormalizeDouble(aiSignal.TakeProfit, _Digits);
+                ResetSweepState();
+                return;
             }

             // Process through sweep logic
@@ -344,7 +346,8 @@
     double upper_band,
     double lower_band,
     double std_dev,
-    bool is_high_velocity)
+    bool is_high_velocity,
+    const SSignal &aiSignal)
 {
     //===============================================================
     // UPPER SWEEP -> POTENTIAL SELL
@@ -374,7 +377,7 @@
         // SELL trigger
         if (tick.bid <= confirmation_level)
         {
-            bool valid = true;
+            bool valid = (aiSignal.Type == 1); // Original SSignal: 1 = SELL

             if (!CanOpenNewTrade(ORDER_TYPE_SELL, tick.bid))
                 valid = false;
@@ -455,7 +458,7 @@
         // BUY trigger
         if (tick.ask >= confirmation_level)
         {
-            bool valid = true;
+            bool valid = (aiSignal.Type == 0); // Original SSignal: 0 = BUY

             if (!CanOpenNewTrade(ORDER_TYPE_BUY, tick.ask))
                 valid = false;
@@ -1088,28 +1091,24 @@
     //+------------------------------------------------------------------+
     //| CHECK MTF CONFIRMATION                                              |
     //+------------------------------------------------------------------+
-    bool CheckMTFConfirmation()
-    {
-        // Check H1, M15, M5 trend alignment
-        double sma_h1  = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE, 0);
-        double price_h1 = iClose(_Symbol, PERIOD_H1, 0);
-
-        bool h1_bullish = price_h1 > sma_h1;
-
-        // Check M15
-        int handle_ma_m15 = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE, 0);
-        double sma_m15  = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE, 0);
-        double price_m15 = iClose(_Symbol, PERIOD_M15, 0);
-        bool m15_bullish = price_m15 > sma_m15;
-
-        // Check M5
-        int handle_ma_m5 = iMA(_Symbol, PERIOD_M5, 20, 0, MODE_EMA, PRICE_CLOSE, 0);
-        double sma_m5  = iMA(_Symbol, PERIOD_M5, 20, 0, MODE_EMA, PRICE_CLOSE, 0);
-        double price_m5 = iClose(_Symbol, PERIOD_M5, 0);
-        bool m5_bullish = price_m5 > sma_m5;
-
-        // All timeframes must agree
-        return (h1_bullish && m15_bullish && m5_bullish);
+    bool CheckMTFConfirmation(const int signal_type)
+    {
+        if (signal_type != 0 && signal_type != 1)
+            return false;
+
+        // Reuse configured handles and closed-bar reads; unavailable data rejects.
+        bool h1_up = false, h1_down = false;
+        bool m15_up = false, m15_down = false;
+        bool m5_up = false, m5_down = false;
+        if (!GetTFTrend(PERIOD_H1, handle_ma_h1, h1_up, h1_down) ||
+            !GetTFTrend(PERIOD_M15, handle_ma_m15, m15_up, m15_down) ||
+            !GetTFTrend(PERIOD_M5, handle_ma_m5, m5_up, m5_down))
+            return false;
+
+        if (signal_type == 0)
+            return (h1_up && m15_up && m5_up);
+
+        return (h1_down && m15_down && m5_down);
     }

     //+------------------------------------------------------------------+
```
