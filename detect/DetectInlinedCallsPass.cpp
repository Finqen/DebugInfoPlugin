// DetectInlinedCallsPass.cpp

#include "llvm/Pass.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/IR/Instructions.h"
#include "llvm/Support/raw_ostream.h"

using namespace llvm;

namespace {

struct DetectInlinedCallsPass : public ModulePass {
  static char ID;
  DetectInlinedCallsPass() : ModulePass(ID) {}

  bool runOnModule(Module &M) override {
    errs() << "=== DetectInlinedCallsPass ===\n";

    for (Module::iterator FI = M.begin(), FE = M.end(); FI != FE; ++FI) {
      Function &F = *FI;
      if (F.isDeclaration())
        continue;

      for (Function::iterator BI = F.begin(), BE = F.end(); BI != BE; ++BI) {
        for (BasicBlock::iterator II = BI->begin(), IE = BI->end(); II != IE; ++II) {
          Instruction &I = *II;

          if (auto *CB = dyn_cast<CallBase>(&I)) {
            const Function *Callee = CB->getCalledFunction();
            if (!Callee || Callee->isDeclaration())
              continue;

            DebugLoc DL = I.getDebugLoc();
            if (!DL)
              continue;

            const DILocation *Scope = DL.get();
            if (Scope && Scope->getInlinedAt()) {
              errs() << "Inlined call detected:\n";
              errs() << "  Caller: " << F.getName() << "\n";
              errs() << "  Callee: " << Callee->getName() << "\n";
              errs() << "  Location: " << Scope->getFilename()
                     << ":" << DL.getLine() << ":" << DL.getCol() << "\n";
            }
          }
        }
      }
    }

    errs() << "=== End of DetectInlinedCallsPass ===\n";
    return false; // This pass does not modify the IR
  }
};

char DetectInlinedCallsPass::ID = 0;

// Register pass for opt
static RegisterPass<DetectInlinedCallsPass>
    X("detect-inlined-calls", "Detect inlined function calls", false, false);

} // namespace
