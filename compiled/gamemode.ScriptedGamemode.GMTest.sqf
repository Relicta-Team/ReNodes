//src:df51195b-0360-45a1-b2b0-348f11983e23:GMTest.graph
//gdate:2024-01-15 20:43:23.723265
#include ".\resdk_graph.h"


editor_attribute("NodeClass")
class(GMTest) extends(ScriptedGamemode)
// Code generated:

//p_field: ctr
["ctr",toString {0}] call pc_oop_regvar;
//p_field: max_time
["max_time",toString {30}] call pc_oop_regvar;
//p_field: name
["name",toString {"Хуйня для пидорасов (титечка)"}] call pc_oop_regvar;
//p_field: desc (default from ScriptedGamemode)
//p_field: descExtended (default from ScriptedGamemode)
//p_field: canAddAspect (default from ScriptedGamemode)
//p_field: duration (default from ScriptedGamemode)
//p_const: _getRolesWrapper
func(_getRolesWrapper) { [ "RHead" ] };
//p_entry: methods.ScriptedGamemode.preSetup_0
func(preSetup) {
    params ['this'];
     
    SCOPENAME "exec"; 
    #ifdef DEBUG
    ["Режим выбран %1", this getVariable "name"] call messageBox_Node;
    #endif
};
//p_entry: methods.ScriptedGamemode.postSetup_0
func(postSetup) {
    params ['this'];
     
    SCOPENAME "exec"; 
    #ifdef DEBUG
    ["Раунд начался! %1", [this] call ((this) getVariable PROTOTYPE_VAR_NAME getVariable "_getRolesWrapper")] call messageBox_Node;
    #endif
};
//p_entry: methods.ScriptedGamemode.onTick_0
func(onTick) {
    params ['this'];
    //init_lv:increment
    private _LVAR1 = 1;
    
    SCOPENAME "exec"; this setVariable ["ctr", (this getVariable "ctr")+(_LVAR1)];
};
//p_entry: methods.ScriptedGamemode._checkFinishWrapper_0
func(_checkFinishWrapper) {
    params ['this'];
     
    SCOPENAME "exec"; if ((this getVariable "ctr")>=(this getVariable "max_time")) then {
        this setVariable ["_currentFinishResult", [1, "Случился конец"]];
    } else {};
};
//p_entry: methods.ScriptedGamemode.onFinish_0
func(onFinish) {
    params ['this'];
     
    SCOPENAME "exec"; 
    #ifdef DEBUG
    ["Конец режима!", [ this getVariable "duration", this getVariable "ctr" ]] call messageBox_Node;
    #endif
};
//p_entry: methods.ScriptedGamemode._conditionToStartWrapper_0
func(_conditionToStartWrapper) {
    params ['this'];
     
    SCOPENAME "exec"; private _lvar_1_0 = [this, "RHead"] call ((this) getVariable PROTOTYPE_VAR_NAME getVariable "getCandidatesCount"); ([!((_lvar_1_0)==0), "Никто не встал"]) BREAKOUT "exec"
};
endclass