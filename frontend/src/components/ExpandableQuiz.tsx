'use client';
import {
  Box,
  Button,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  VStack,
  HStack,
  Text,
  Heading,
  Radio,
  RadioGroup,
  Input,
  Badge,
  useToast
} from '@chakra-ui/react';
import { useState, useCallback } from 'react';
import { useGraph } from '@/contexts/GraphContext';
import { useMode } from '@/contexts/ModeContext';
import { api } from '@/services/api';

interface QuizQuestion {
  type: 'multiple_choice' | 'true_false' | 'short_answer';
  question: string;
  options?: string[];
  correct_answer: string;
  explanation: string;
  concept_id: string;
}

export function ExpandableQuiz() {
  const { graph, currentRequestId } = useGraph();
  const { currentMode } = useMode();
  const [isOpen, setIsOpen] = useState(false);
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [showResults, setShowResults] = useState(false);
  const [score, setScore] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const toast = useToast();
  
  const generateQuiz = useCallback(async () => {
    if (!graph || graph.nodes.length === 0) return;
    
    // Check if learning path is built (concepts should have learningPathPosition)
    const conceptsWithPath = graph.nodes.filter(node => node.data?.learningPathPosition !== undefined && node.data?.learningPathPosition !== null);
    if (conceptsWithPath.length === 0) {
      toast({
        title: 'Learning Path Required',
        description: 'Please build the learning path first before generating quiz',
        status: 'warning',
        duration: 4000,
        isClosable: true
      });
      return;
    }
    
    if (!currentRequestId) {
      toast({
        title: 'Error',
        description: 'Request ID not found. Please submit a new query.',
        status: 'error',
        duration: 5000
      });
      return;
    }
    
    setIsGenerating(true);
    try {
      // Call API to generate quiz
      const response = await api.generateQuiz(currentRequestId, 5);
      
      if (response.questions && response.questions.length > 0) {
        setQuestions(response.questions);
        setCurrentQuestion(0);
        setAnswers({});
        setShowResults(false);
        setScore(0);
      } else {
        toast({
          title: 'No Questions Generated',
          description: 'Failed to generate quiz questions',
          status: 'warning',
          duration: 3000
        });
      }
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to generate quiz',
        status: 'error',
        duration: 5000
      });
    } finally {
      setIsGenerating(false);
    }
  }, [graph, currentRequestId, toast]);
  
  // Don't auto-generate quiz - user must click button after learning path is built
  // useEffect removed - quiz generation is now manual
  
  // Only show in study mode when graph has nodes
  if (currentMode !== 'study' || !graph || graph.nodes.length === 0) {
    return null;
  }
  
  const handleAnswer = (answer: string) => {
    setAnswers(prev => ({ ...prev, [currentQuestion]: answer }));
  };
  
  const handleNext = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(prev => prev + 1);
    } else {
      calculateScore();
      setShowResults(true);
    }
  };
  
  const calculateScore = () => {
    let correct = 0;
    questions.forEach((q, idx) => {
      if (answers[idx] === q.correct_answer) {
        correct++;
      }
    });
    setScore(correct);
  };
  
  const question = questions[currentQuestion];
  const userAnswer = answers[currentQuestion];
  
  return (
    <Box position="absolute" top={4} left={120} zIndex={10}>
      <Popover isOpen={isOpen} onOpen={() => setIsOpen(true)} onClose={() => setIsOpen(false)} placement="bottom-start">
        <PopoverTrigger>
          <Button size="sm" colorScheme="green" variant="outline">
            Quiz
          </Button>
        </PopoverTrigger>
        <PopoverContent w="400px" maxH="600px" overflowY="auto">
          <PopoverBody>
            {questions.length === 0 ? (
              <VStack spacing={4}>
                <Text fontSize="sm" color="gray.500">
                  {graph.nodes.some(n => n.data?.learningPathPosition !== undefined && n.data?.learningPathPosition !== null) 
                    ? 'Generate quiz questions from your study concepts'
                    : 'Build learning path first to generate quiz questions'}
                </Text>
                <Button 
                  size="sm" 
                  colorScheme="blue" 
                  onClick={generateQuiz}
                  isDisabled={!graph.nodes.some(n => n.data?.learningPathPosition !== undefined && n.data?.learningPathPosition !== null) || isGenerating}
                  isLoading={isGenerating}
                  loadingText="Generating..."
                >
                  Generate Quiz
                </Button>
              </VStack>
            ) : !showResults ? (
              <VStack align="stretch" spacing={4}>
                <HStack justify="space-between">
                  <Heading size="sm">Quiz</Heading>
                  <Text fontSize="xs" color="gray.500">
                    Question {currentQuestion + 1} of {questions.length}
                  </Text>
                </HStack>
                
                <Text fontSize="md" fontWeight="medium">
                  {question.question}
                </Text>
                
                {question.type === 'multiple_choice' && question.options && (
                  <RadioGroup value={userAnswer || ''} onChange={handleAnswer}>
                    <VStack align="stretch" spacing={2}>
                      {question.options.map((option, idx) => (
                        <Radio key={idx} value={option}>
                          {option}
                        </Radio>
                      ))}
                    </VStack>
                  </RadioGroup>
                )}
                
                {question.type === 'true_false' && (
                  <RadioGroup value={userAnswer || ''} onChange={handleAnswer}>
                    <VStack align="stretch" spacing={2}>
                      <Radio value="true">True</Radio>
                      <Radio value="false">False</Radio>
                    </VStack>
                  </RadioGroup>
                )}
                
                {question.type === 'short_answer' && (
                  <Input
                    value={userAnswer || ''}
                    onChange={(e) => handleAnswer(e.target.value)}
                    placeholder="Your answer..."
                  />
                )}
                
                <HStack spacing={2}>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setCurrentQuestion(prev => Math.max(0, prev - 1))}
                    isDisabled={currentQuestion === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="blue"
                    onClick={handleNext}
                    isDisabled={!userAnswer}
                    flex={1}
                  >
                    {currentQuestion === questions.length - 1 ? 'Finish' : 'Next'}
                  </Button>
                </HStack>
              </VStack>
            ) : (
              <VStack align="stretch" spacing={4}>
                <HStack justify="space-between">
                  <Heading size="sm">Quiz Complete!</Heading>
                  <Badge colorScheme={score >= questions.length / 2 ? 'green' : 'red'}>
                    {score}/{questions.length}
                  </Badge>
                </HStack>
                <Text fontSize="md">
                  You scored {score} out of {questions.length}
                </Text>
                <Button size="sm" colorScheme="blue" onClick={() => {
                  setShowResults(false);
                  setCurrentQuestion(0);
                  setAnswers({});
                }}>
                  Retake Quiz
                </Button>
              </VStack>
            )}
          </PopoverBody>
        </PopoverContent>
      </Popover>
    </Box>
  );
}
